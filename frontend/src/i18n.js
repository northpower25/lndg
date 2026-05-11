import i18n from 'i18next'
import { initReactI18next } from 'react-i18next'
import en from './locales/en.json'
import de from './locales/de.json'

// Detect language from <html lang="…"> set by Django's LocaleMiddleware,
// falling back to browser preference and then English.
const htmlLang = document.documentElement.lang || navigator.language || 'en'
const detectedLang = htmlLang.startsWith('de') ? 'de' : 'en'

i18n
  .use(initReactI18next)
  .init({
    resources: {
      en: { translation: en },
      de: { translation: de },
    },
    lng: detectedLang,
    fallbackLng: 'en',
    interpolation: { escapeValue: false },
  })

export default i18n
