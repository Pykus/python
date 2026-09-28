<script setup>
import { reactive, ref } from "vue"

const API_BASE = ""

const form = reactive({
  name: "",
  room: "",
  enabled: true,
  note: "",
})

const fieldErrors = reactive({})
const globalError = ref("")
const result = ref(null)
const saving = ref(false)

function clearErrors() {
  globalError.value = ""
  for (const key of Object.keys(fieldErrors)) {
    delete fieldErrors[key]
  }
}

async function submit() {
  clearErrors()
  saving.value = true
  result.value = null

  try {
    const response = await fetch(`${API_BASE}/api/devices`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(form),
    })

    const payload = await response.json().catch(() => ({}))

    if (response.status === 422 && Array.isArray(payload.errors)) {
      for (const error of payload.errors) {
        if (error.field && error.field !== "_request") {
          fieldErrors[error.field] = error.message
        } else {
          globalError.value = error.message || "The request is invalid."
        }
      }
      return
    }

    if (!response.ok) {
      globalError.value = `Request failed with HTTP ${response.status}.`
      return
    }

    result.value = payload.device
  } catch (error) {
    globalError.value = "The API could not be reached."
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <form @submit.prevent="submit">
    <label>
      Device name
      <input v-model="form.name" autocomplete="off">
      <small v-if="fieldErrors.name">{{ fieldErrors.name }}</small>
    </label>

    <label>
      Room
      <input v-model="form.room" autocomplete="off">
      <small v-if="fieldErrors.room">{{ fieldErrors.room }}</small>
    </label>

    <label>
      Note
      <textarea v-model="form.note"></textarea>
      <small v-if="fieldErrors.note">{{ fieldErrors.note }}</small>
    </label>

    <label>
      <input v-model="form.enabled" type="checkbox">
      Enabled
    </label>

    <p v-if="globalError" role="alert">{{ globalError }}</p>

    <button :disabled="saving" type="submit">
      {{ saving ? "Saving..." : "Save device" }}
    </button>

    <pre v-if="result">{{ result }}</pre>
  </form>
</template>
