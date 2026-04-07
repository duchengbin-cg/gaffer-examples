import os

import Gaffer
import GafferUI

# 可选依赖：某些环境下没有 Arnold 插件。为避免 UI startup 脚本整体崩溃，必须保护性导入。
try:
    import GafferArnold  # noqa: F401
except Exception:
    pass

# 最稳健的“延迟注入”方案：
# 不在脚本顶层尝试获取 Application；而是等 ScriptWindow 真正创建后，
# 再对对应的 ScriptNode 注入 project:root，并绑定 fileNameChangedSignal()。


def __findProjectRootFromFileName(fileName):
    """从脚本文件路径推断工程根目录（统一为 posix 风格路径）。"""

    projectDir = os.path.dirname(os.path.abspath(fileName)).replace("\\", "/")

    # 用户常从 templates 目录打开文件，向上回到工程根目录
    if "templates" in projectDir.split("/"):
        projectDir = os.path.dirname(projectDir).replace("\\", "/")

    # 进一步向上追溯：若存在 assets 目录，则认为当前为工程根目录
    candidate = projectDir
    for _ in range(6):
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

    # 供 .gfr/.grf 内 ${project:root} 使用
    script.context()["project:root"] = projectDir

    # 同步环境变量，方便外部插件/工具使用
    os.environ["GAFFER_EXAMPLES"] = projectDir


def __installForScript(script):
    """为单个 ScriptNode 安装自动更新逻辑（避免重复连接信号）。"""

    marker = "_aduProjectRootInstalled"
    if getattr(script, marker, False):
        return
    setattr(script, marker, True)

    # 初次（打开文件）立刻更新一次
    __updateProjectRoot(script)

    # 后续 Save As / 改名，也要跟随更新
    # 适配不同版本的信号名：
    # - Gaffer 1.6 常用 pathChangedSignal()
    # - 部分旧环境可能仍为 fileNameChangedSignal()
    signal = getattr(script, "pathChangedSignal", getattr(script, "fileNameChangedSignal", None))
    if signal:
        signal().connect(lambda s: __updateProjectRoot(s))


def __onScriptWindowCreated(scriptWindow):
    script = scriptWindow.scriptNode()
    __installForScript(script)


# 在 Gaffer 1.6 中最安全：等窗口真正创建时才触发
if hasattr(GafferUI, "ScriptWindow") and hasattr(GafferUI.ScriptWindow, "instanceCreatedSignal"):
    GafferUI.ScriptWindow.instanceCreatedSignal().connect(__onScriptWindowCreated)
