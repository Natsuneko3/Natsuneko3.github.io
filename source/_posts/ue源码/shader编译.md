---
title: shader编译
date: 2022-04-10 12:00
tags:
- 笔记
- GPU
category: 图形学笔记
count: true
---
# shader编译

shader的编译是由RecompileShader命令去处理过程，里面是BeginRecompileGlobalShaders开始编译指定的shader，shader的编译作业由全局对象GShaderCompilingManager完成，最终的shader编译作业实例类型是FShaderCommonCompileJob，它的实例对进入一个全局的队列，以便多线程异步地编译。
FShaderCompilingManager::AddJobs等接口加入到FShaderCompilingManager::CompileQueue队列中，然后主要由FShaderCompileThreadRunnable::PullTasksFromQueue接口拉取作业并执行
Ue多平台语言转换方案，Vulkan不但拥有全新的API，还带来了一个新的shader中间格式SPIR-V。这正是通往统一的跨平台shader编译路上最更要的一级台阶

![Untitled](Untitled.png)