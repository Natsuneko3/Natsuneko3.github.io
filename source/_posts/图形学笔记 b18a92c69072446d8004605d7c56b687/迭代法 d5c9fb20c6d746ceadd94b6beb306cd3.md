---
title: 迭代法
date: 2022-04-07 12:00
tags: 图形学笔记
category: 笔记
---
# 迭代法

## 牛顿迭代法

![Untitled](Untitled.png)

# Jocobi迭代法

x为我们要求的公式，例如隐性弹簧质点系统的v,A为要求的方程，就是质点弹簧公式

![Untitled](Untitled%201.png)

# 高斯-赛德尔迭代（Gauss–Seidel method）

![Untitled](Untitled%202.png)

![Untitled](Untitled%203.png)

高斯迭代法和jocobi迭代法类似，jocobi用的是上一个值，高斯用的是当前值，
高斯迭代适用于大型稀疏线性方程组，本质上是串行计算，其需要保留上一帧所有顶点坐标的值，所以不利于并行计算，但其收敛速度较快，模拟更准确。
Jocobi有着更好的并行计算