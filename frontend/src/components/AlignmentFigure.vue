<template>
  <figure class="card p-8" aria-label="多译本数据结构示意">
    <div class="kicker">Parallel alignment</div>
    <h2 class="mt-3 font-display text-2xl font-semibold">一个原文范围，多个译本</h2>
    <div class="mt-6 rounded-lg border border-line bg-surface-2 p-4 text-sm">作品 → 段落 → 对齐句组</div>
    <div class="mt-4 grid gap-3">
      <div v-for="label in ['甲译本', '乙译本', '丙译本']" :key="label" class="rounded-lg border border-line p-4">
        <div class="text-sm font-medium text-accent">{{ label }}</div>
        <div class="mt-2 text-sm text-ink-2">原文片段 ↔ 对应译文</div>
        <div class="mt-2 text-xs text-muted">句对 → 标注项组 → 标注项</div>
      </div>
    </div>
    <figcaption class="mt-4 text-xs leading-6 text-muted">结构示意。系统不附带任何实际语料或标注记录。</figcaption>
  </figure>
</template>
