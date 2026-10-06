<script setup lang="ts">
import { site } from '@/site'
</script>

<template>
  <div class="mx-auto max-w-4xl px-4 py-10 sm:px-6 sm:py-14">
    <h1 class="font-display text-3xl font-semibold">引用规范</h1>
    <section class="mt-8 space-y-4 text-sm leading-7 text-ink-2">
      <p>{{ site.name }} 使用 RuCorpus 开源软件运行。研究引用应区分软件和本安装实例的语料来源。</p>
      <div class="card p-6">
        <h2 class="font-display text-xl font-semibold text-ink">软件出处</h2>
        <p class="mt-3">RuCorpus: Russian-first Parallel Corpus Search System.</p>
        <a href="https://github.com/RobLinkA/rucorpus" class="text-accent underline break-all">https://github.com/RobLinkA/rucorpus</a>
        <p class="mt-3 text-muted">建议注明使用的提交版本和访问日期。软件使用 MIT 许可证，学术引用是建议。</p>
      </div>
      <div class="card p-6">
        <h2 class="font-display text-xl font-semibold text-ink">语料与标注出处</h2>
        <p class="mt-3">由本站运营者提供语料版权、标注来源、书目信息和所需引用文献。开源软件不附带语料，软件许可证也不授予任何文本或数据的使用权。</p>
        <RouterLink to="/help#sources" class="text-accent underline">查看当前安装实例的版本与出处</RouterLink>
      </div>
    </section>
  </div>
</template>
