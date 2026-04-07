import os

import Gaffer
import GafferUI

# 在 GUI 启动时自动注入 project:root，并同步 GAFFER_EXAMPLES 环境变量。
# 目标：工程目录可移动（D盘/E盘/网络盘都可），打开 .gfr 后自动指向当前所在位置。


def __findProjectRootFromFileName(fileName):
    """从脚本文件路径推断工程根目录（统一为 posix 风格路径）。"""

    projectDir = os.path.dirname(os.path.abspath(fileName)).replace("\\", "/")

    # 用户常从 templates 目录打开文件，向上回到工程根目录
    if "templates" in projectDir.split("/"):
        projectDir = os.path.dirname(projectDir).replace("\\", "/")

    # 进一步向上追溯：若存在 assets 目录，则认为当前为工程根目录；
    # 否则保持当前推断结果（兼容用户自定义结构）。
    candidate = projectDir
    for _ in range(5):
        if os.path.isdir(os.path.join(candidate, "assets")):
            projectDir = candidate.replace("\\", "/")
            break
        parent = os.path.dirname(candidate)
        if parent == candidate:
            break
        candidate = parent

    return projectDir


def __updateProjectRoot(script):
    fileName = script["fileName"].getValue()
    if not fileName:
        return

    projectDir = __findProjectRootFromFileName(fileName)

    # Context 变量（供 .gfr/.grf 内 ${project:root} 使用）
    script.context()["project:root"] = projectDir

    # 同步环境变量（供外部插件/工具使用）
    os.environ["GAFFER_EXAMPLES"] = projectDir


def __installForScript(script):
    """为单个 ScriptNode 安装自动更新逻辑（避免重复连接信号）。"""

    # 防止重复安装
    marker = "_aduProjectRootInstalled"
    if getattr(script, marker, False):
        return
    setattr(script, marker, True)

    # 初次（打开文件）立刻更新一次
    __updateProjectRoot(script)

    # 后续 Save As / 改名，也要跟随更新
    script.fileNameChangedSignal().connect(lambda s: __updateProjectRoot(s))


def __installViaApplication(application):
    """如果能拿到 application，就监听 scripts 容器，实现全局覆盖。"""

    try:
        scripts = application.root()["scripts"]
    except Exception:
        return

    def __onScriptAdded(container, script):
        __installForScript(script)

    scripts.instanceAddedSignal().connect(__onScriptAdded)


def __install():
    """更健壮的安装入口：
    - 优先从 Editor.root() 推断 application（若 GafferUI.Application 存在）
    - 如果拿不到 application，则退化为监听 ScriptWindow 的创建信号，
      对每个 ScriptWindow 对应的 ScriptNode 做注入。
    """

    # 方式 1：按你建议的方式，从 Editor.root() 找 application
    applicationClass = getattr(GafferUI, "Application", None)
    if applicationClass is not None:
        try:
            application = GafferUI.Editor.root().ancestor(applicationClass)
        except Exception:
            application = None

        if application is not None:
            __installViaApplication(application)
            return

    # 方式 2：延迟注入（更通用）：当 ScriptWindow 出现时安装
    scriptWindowClass = getattr(GafferUI, "ScriptWindow", None)
    if scriptWindowClass is None:
        return

    instanceCreatedSignal = getattr(scriptWindowClass, "instanceCreatedSignal", None)
    if instanceCreatedSignal is None:
        # 老版本若没有 instanceCreatedSignal，就无法可靠安装；直接返回
        return

    def __onScriptWindowCreated(scriptWindow):
        try:
            __installForScript(scriptWindow.scriptNode())
        except Exception:
            pass

    instanceCreatedSignal().connect(__onScriptWindowCreated)


__install()
