<template>
  <div class="word-card" :class="{ flipped: isFlipped }" @click="toggleFlip">
    <div class="card-inner">
      <div class="card-front">
        <div class="word-header">
          <h1 class="word-text">{{ word.word }}</h1>
          <p v-if="word.phonetic" class="phonetic">{{ word.phonetic }}</p>
        </div>
        <div class="hint">
          <n-text depth="3">点击卡片查看详情</n-text>
        </div>
      </div>

      <div class="card-back">
        <div class="word-content">
          <div class="word-header-small">
            <h2>{{ word.word }}</h2>
            <p v-if="word.phonetic" class="phonetic-small">{{ word.phonetic }}</p>
          </div>

          <n-divider />

          <div class="definitions">
            <h3>释义</h3>
            <div v-for="(def, index) in word.definitions" :key="index" class="definition-item">
              <n-tag :bordered="false" size="small" type="info">{{ def.pos }}</n-tag>
              <p class="def-cn">{{ def.cn }}</p>
              <p class="def-en">{{ def.en }}</p>
            </div>
          </div>

          <n-divider v-if="word.sentences && word.sentences.length > 0" />

          <div v-if="word.sentences && word.sentences.length > 0" class="sentences">
            <h3>例句</h3>
            <div v-for="(sentence, index) in word.sentences" :key="index" class="sentence-item">
              <p class="sentence-en">{{ sentence.en }}</p>
              <p class="sentence-cn">{{ sentence.cn }}</p>
            </div>
          </div>

          <n-divider v-if="word.mnemonic" />

          <div v-if="word.mnemonic" class="mnemonic">
            <h3>记忆法</h3>
            <p>{{ word.mnemonic }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { NText, NTag, NDivider } from 'naive-ui'
import type { Word } from '@/types'

interface Props {
  word: Word
}

defineProps<Props>()

const isFlipped = ref(false)

function toggleFlip() {
  isFlipped.value = !isFlipped.value
}
</script>

<style scoped>
.word-card {
  width: 100%;
  max-width: 600px;
  height: 500px;
  perspective: 1000px;
  cursor: pointer;
}

.card-inner {
  position: relative;
  width: 100%;
  height: 100%;
  transition: transform 0.6s;
  transform-style: preserve-3d;
}

.word-card.flipped .card-inner {
  transform: rotateY(180deg);
}

.card-front,
.card-back {
  position: absolute;
  width: 100%;
  height: 100%;
  backface-visibility: hidden;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
  background: white;
  padding: 40px;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.card-front {
  justify-content: center;
  align-items: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.card-back {
  transform: rotateY(180deg);
  overflow-y: auto;
}

.word-header {
  text-align: center;
}

.word-text {
  font-size: 48px;
  font-weight: bold;
  margin: 0;
  margin-bottom: 16px;
}

.phonetic {
  font-size: 24px;
  opacity: 0.9;
  margin: 0;
}

.hint {
  margin-top: 40px;
  opacity: 0.8;
}

.word-header-small {
  text-align: center;
  margin-bottom: 16px;
}

.word-header-small h2 {
  font-size: 32px;
  margin: 0 0 8px 0;
}

.phonetic-small {
  font-size: 18px;
  color: #666;
  margin: 0;
}

.word-content h3 {
  font-size: 18px;
  font-weight: 600;
  margin: 16px 0 12px 0;
  color: #333;
}

.definitions {
  margin-bottom: 16px;
}

.definition-item {
  margin-bottom: 16px;
}

.definition-item .n-tag {
  margin-bottom: 8px;
}

.def-cn {
  font-size: 16px;
  font-weight: 500;
  margin: 8px 0 4px 0;
  color: #333;
}

.def-en {
  font-size: 14px;
  color: #666;
  margin: 0;
}

.sentences {
  margin-bottom: 16px;
}

.sentence-item {
  margin-bottom: 12px;
  padding: 12px;
  background: #f5f5f5;
  border-radius: 8px;
}

.sentence-en {
  font-size: 14px;
  margin: 0 0 8px 0;
  color: #333;
}

.sentence-cn {
  font-size: 14px;
  margin: 0;
  color: #666;
}

.mnemonic {
  margin-bottom: 16px;
}

.mnemonic p {
  font-size: 14px;
  line-height: 1.6;
  color: #666;
  background: #fff9e6;
  padding: 12px;
  border-radius: 8px;
  border-left: 4px solid #ffd700;
}
</style>
