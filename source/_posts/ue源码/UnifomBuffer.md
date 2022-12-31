---
title: UnifomBuffer
date: 2022-04-10 12:00
tags:
- 笔记
- UE源码
category: UE源码笔记
count: true
---
# UnifomBuffer

Uniform Buffer涉及了几个核心的概念，最底层的是RHI层的FRHIUniformBuffer，封装了各种图形API的统一缓冲区（也叫Constant Buffer）

![Untitled](Untitled.png)

如果项目处于开发阶段，最好将Shader的编译选项改成Development，可以通过修改Engine\Config\ConsoleVariables.ini

![Untitled](Untitled%201.png)

![Untitled](Untitled%202.png)