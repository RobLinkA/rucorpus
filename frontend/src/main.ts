import { createPinia } from 'pinia'
import { createApp } from 'vue'
import App from './App.vue'
import router from './router'
import './style.css'
import { site } from './site'

document.title = site.name

createApp(App).use(createPinia()).use(router).mount('#app')
