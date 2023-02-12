---
title: HZB (Hierarchical Z-Buffer)
date: 2022-04-07 12:00
count: true
tags: 
- 图形学笔记
- 渲染
category: 图形学笔记
---
# HZB (Hierarchical Z-Buffer)

HZB是多Mip层级的z-buffer，也就是说depthmap的lod，每个更高级别Mip的buffer记录上一级别中周围四点中最远处的深度值。

![Untitled](Untitled.png)

将HZB生成后，就可以将待剔除物体的包围盒信息传入到Computer Shader中进行计算，计算时会选择最适合的Mip级别进行遮挡测试。在屏幕中占比更大的物体会选择更高级别Mip的深度进行测试，这样可以降低计算量。

计算hzb时候的计算了是非常小的，昂贵的是从gpu传输到cpu上

![Untitled](Untitled%201.png)

![Untitled](Untitled%202.png)