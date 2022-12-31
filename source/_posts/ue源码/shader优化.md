---
title: shader优化
date: 2022-04-10 12:00
tags:
- 笔记
- GPU
category: 图形学笔记
count: true
---
# shader优化

- 避免if、switch分支语句。
- 避免for循环语句，特别是循环次数可变的。
- 减少纹理采样次数。
- 禁用clip或discard操作。
- 减少复杂数学函数调用。
- 使用更低精度的浮点数。OpenGL ES的浮点数有三种精度：highp（32位浮点）, mediump（16位浮点）, lowp（8位浮点），很多计算不需要高精度，可以改成低精度浮点。
- 充分利用向量分量掩码。
    
    ![Untitled](Untitled.png)
    
- 避免重复计算。可以将所有像素一样的变量提前计算好，或者由C++层传入：
    
    ![Untitled](Untitled%201.png)
    
- • 向量延迟计算。
    
    ![Untitled](Untitled%202.png)
    
- 避免或减少临时变量。
- 尽量将Pixel Shader计算移到Vertex Shader。例如像素光改成顶点光。
- [将跟顶点或像素无关的计算移到CPU，然后通过uniform传进来。既上面的全部像素一样的变量](https://www.cnblogs.com/timlly/p/15092257.html#:~:text=%E8%89%B2%E5%99%A8%E5%8F%82%E6%95%B0.-,MyColorParameter,-.Bind(Initializer.ParameterMap)
- 分级策略。不同画质不同平台采用不同复杂度的算法。
- 顶点输入应当采用逐Structure的布局，避免每个顶点属性一个数组。逐Structure的布局有利于提升GPU缓存命中率。
- 尽可能用Compute Shader代替传统的VS、PS管线。CS的管线更加简单、纯粹，利于并行化计算，结合LDS机制，可有效提升效率。
- 降分辨率渲染。有些信息没有必要全分配率渲染，如模糊的倒影、SSR、SSGI等。

static TAutoConsoleVariable function（）可以添加命令控制台，
function.GetValueOnAnyThread()可以获取当前控制台的值

![Untitled](Untitled%203.png)