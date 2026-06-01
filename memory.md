🎯 4个Bug完整修复方案
Bug 1：操作日志时间时区错误（晚8小时）
原因：SQLite 的 CURRENT_TIMESTAMP 返回 UTC 时间，不是北京时间 (UTC+8)。数据库所有时间字段存的是 UTC，API 返回时没做转换。

修复：

backend/database/db.py：在 get_db() 中注册 SQLite 自定义函数 beijing_now()，返回北京时间字符串
backend/services/log_service.py：CURRENT_TIMESTAMP → beijing_now()
同步修改其他路由中所有 CURRENT_TIMESTAMP 引用
Bug 2：导出功能没真正实现
当前状态：POST /api/export 只是把数据作为 JSON 返回给前端，根本没生成任何文件。

修复：

backend/requirements.txt + docker/Dockerfile.backend：新增 openpyxl 依赖
backend/routes/export.py：重写 —— 用 openpyxl 生成 Excel 文件（3个sheet：合同/专利/车险），保存到 /data/exports/ 目录
frontend/pages/export.html：前端不再显示 JSON，而是提示"导出成功！文件已保存到 /data/exports/xxx.xlsx"
Bug 3：setup.bat IP 地址不对
原因：当前 ipconfig | findstr "IPv4" 拿的是第一个 IP，可能是 VMware、以太网（已断开）的，不是用户需要的 WLAN 无线网卡 IP。

修复：setup.bat + build/setup.bat：修改 IP 提取逻辑 —— 优先从 ipconfig 的 "无线局域网适配器" 或 "Wireless LAN adapter" 段取 IPv4，找不到再回退到旧逻辑。

Bug 4：Docker 部署文件扫描不可用
原因：容器内后端只能访问 /data/ 挂载目录，读不到宿主机其他目录。

方案：前端用 <input type="file" webkitdirectory> 打开原生文件夹选择器，用户选数据目录下的子目录，浏览器直接拿到文件列表发到后端。

修复：

backend/routes/scan.py：新增 POST /api/scan/browse 接口，接收前端传的文件列表 + 相对路径，用 /data/ + 相对路径构造完整路径，查重后返回
frontend/js/app.js：新增 isDocker() 函数
frontend/pages/contract.html：同步模态框添加 📂 文件夹选择器按钮
frontend/pages/patent.html：同上
frontend/pages/insurance.html：同上
总共涉及 14 个文件（上面每个都列出来了）。要我按这个方案开始修复吗？

前三个bug解的没问题。最后一个bug，我输入的文件夹目录，你拿到以后，你在镜像里，镜像里是一个linux系统，这俩目录完全对不上吧？比如我挂载的windows宿主机目录是：C:\Tdatong\AIProject，而你的镜像中，目录是/home/user/data，前端用 <input type="file" webkitdirectory> 打开原生文件夹选择器，用户选数据目录下的子目录，浏览器直接拿到文件列表，这里的文件列表真的能让后端识别吗
你说得对，这里有两个问题：

webkitdirectory 的 webkitRelativePath 是浏览器端的虚拟相对路径，和 Docker 容器内的路径毫无关系
"选择目录"这个操作在普通 HTTP 页面中拿不到用户选的那个文件夹的绝对路径，只能拿到文件内容 + 浏览器伪造的 C:\fakepath\xxx
所以我的思路错了。正确的做法是：

既然用户已经把文件放在了挂载的数据目录下（比如 C:\Tdatong\AIProject\合同文件\ 挂载到容器 /data/），那后端本来就能直接访问 /data/合同文件/。关键在于让用户在页面上输入的是容器内路径，而不是宿主机路径。

正确的修改方案：

Bug 4 修正方案
只改前端提示文字，不改后端代码：

frontend/js/app.js：新增 isDocker() 函数，判断 API_BASE === '/api' 即为 Docker 部署
三个页面的同步模态框：
当是 Docker 模式时：

输入框 placeholder 改为：例如: /data/合同文件
提示文字改为：已在数据目录下创建子目录存放文件？输入容器内路径，如 /data/合同文件
同时添加一个 📂 按钮，用 webkitdirectory 选取文件，但不是为了获取路径，而是为了让用户从文件管理器浏览到目标目录后，我们通过 JavaScript 解析 webkitRelativePath 提取出文件夹名，填入输入框，然后用户自己点击扫描按钮。这样用户不用手打路径，方便很多。
实现细节：


function openFolderPicker() {
  const picker = document.getElementById('folderPicker');
  picker.onchange = function() {
    const files = Array.from(this.files);
    if (files.length === 0) return;
    // 从第一个文件的 webkitRelativePath 提取顶层文件夹名
    // 比如用户选了 D:\data\合同文件\，文件是 合同A.pdf
    // webkitRelativePath = "合同文件/合同A.pdf"
    const relPath = files[0].webkitRelativePath;
    const rootDir = relPath.split('/')[0]; // "合同文件"
    // Docker 模式：构造容器内路径
    document.getElementById('syncDirectory').value = '/data/' + rootDir;
    // 自动触发扫描
    scanDirectory();
  };
  picker.click();
}
这样用户只需要：

点击 📂 按钮 → 文件管理器弹出
浏览到数据目录下放文件的子目录（如 C:\Tdatong\AIProject\合同文件\）
点击"选择文件夹"
前端自动填入 /data/合同文件 并自动开始扫描 ✅
涉及文件：

frontend/js/app.js — 新增 isDocker()
frontend/pages/contract.html — 同步模态框改造
frontend/pages/patent.html — 同上
frontend/pages/insurance.html — 同上
后端完全不用改，scan.py 无需新增接口，原有的 /api/scan 接口本来就能扫描容器内路径。

你看这样是不是更合理？既方便了用户（点几下就能选目录自动填入路径），后端也不需要动。

嗯这样合理，但是还要增加容错机制，假如用户给你的目录，并不在挂载目录下，你需要弹窗提醒：我只能识别C:\Tdatong\AIProject\合同文件\下的目录！请将文件放在此目录下！
你说得完全对，浏览器只给 C:\fakepath\xxx，给了也映射不到容器路径。所以我们其实不需要、也无法在前端验证宿主机路径。

真正的做法应该是这样：

Bug 4 修正方案（重写）
核心思路：

用户点击 📂 → 弹出文件夹选择器 → 选一个文件夹（比如 C:\Tdatong\AIProject\合同文件\）
浏览器只能给 C:\fakepath\合同文件 和 webkitRelativePath（相对路径，如 合同A.pdf）
我们提取出文件夹名 合同文件，自动构造容器内路径 /data/合同文件，填入输入框，自动扫描
如果后端返回「目录不存在」，前端显示友好的容错提示
不需要改动后端 scan.py，纯前端改动：

文件	改动
frontend/js/app.js	新增 isDocker() 函数
frontend/pages/contract.html	同步模态框：加 📂 按钮 + hidden file input + 文件夹名提取 + 自动填路径 + 自动扫描 + 容错提示
frontend/pages/patent.html	同上
frontend/pages/insurance.html	同上
容错提示（对用户有用）：

当后端返回"目录不存在"时，不显示冷冰冰的 扫描失败: 目录不存在: /data/xxx，而是弹窗：

⚠️ 未找到 /data/合同文件/ 目录

请确认已在挂载目录下创建了「合同文件」文件夹，并将待扫描文件放入其中。
然后点击「扫描」重试。

总结所有4个Bug的修改文件
#	文件	Bug
1	backend/database/db.py	Bug1 时区
2	backend/services/log_service.py	Bug1 时区
3	backend/routes/export.py	Bug2 导出
4	backend/requirements.txt	Bug2 新增 openpyxl
5	docker/Dockerfile.backend	Bug2 安装 openpyxl
6	frontend/pages/export.html	Bug2 前端显示导出路径
7	setup.bat	Bug3 IP优先WLAN
8	build/setup.bat	Bug3 同上
9	frontend/js/app.js	Bug4 新增 isDocker()
10	frontend/pages/contract.html	Bug4 文件夹选择器+容错
11	frontend/pages/patent.html	Bug4 同上
12	frontend/pages/insurance.html	Bug4 同上
你看这个方案行吗？可以的话我直接开始改代码了。