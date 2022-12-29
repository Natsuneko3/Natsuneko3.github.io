---
title: Ambient Cube
date: 2022-04-07 12:00
count: true
tags: 
- 图形学笔记 
- 渲染
category: 图形学笔记
---
# Ambient Cube

ambient cube 是 valve 在2004年开发半条命2使用的一个提供间接光的技术。该方法的资料不多，核心思想是将一个vpl看作一个cube。cube有六个面，每个面中存放相对于的颜色。在evaluation阶段，通过法线去索引这六个面中的3个面，最后通过权重去做混合。

六个float3的参数，带宽占用在2阶球谐和3阶球谐之间。效果基本上和2阶球谐一样。优势在于evaluation阶段，alu开销小于2阶球谐，在移动端中的性能要好一些。

![Untitled](Untitled.png)

![Untitled](Untitled%201.png)