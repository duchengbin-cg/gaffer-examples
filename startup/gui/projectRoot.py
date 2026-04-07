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


def __onScriptAdded(container, script):
    # 初次添加（打开文件）立刻更新一次
    __updateProjectRoot(script)

    # 后续如果用户执行 Save As / 改名，也要跟随更新
    script.fileNameChangedSignal().connect(lambda s: __updateProjectRoot(s))


def __install(application):
    # 监听所有 ScriptNode 的创建/加载
    scripts = application.root()["scripts"]
    scripts.instanceAddedSignal().connect(__onScriptAdded)


__install(GafferUI.Application.instance())

