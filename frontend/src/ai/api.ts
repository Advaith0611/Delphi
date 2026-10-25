import axios from 'axios'
import type { GenerationRequest, GenerationResponse } from '../types'
import { generateLocalInterface } from './localGenerator'

const API_URL = import.meta.env.VITE_API_URL ?? (import.meta.env.DEV ? 'http://localhost:8000' : 'https://pythois.onrender.com')
const GENERATE_TIMEOUT_MS = 30000

function generationErrorMessage(error: unknown) {
  if (!axios.isAxiosError(error)) return error instanceof Error ? error.message : String(error)

  const status = error.response?.status
  const detail = error.response?.data
  if (status) return `Generate API returned ${status}: ${typeof detail === 'string' ? detail : JSON.stringify(detail)}`
  if (error.code === 'ECONNABORTED') return 'Generate API timed out'
  return error.message
}

function localFallbackResponse(request: GenerationRequest): GenerationResponse {
  return {
    actionBatch: {
      schemaVersion: 'pythios.canvas.actions.v1',
      actions: [],
    },
    generatedUI: generateLocalInterface(request),
    source: 'ai-core',
  }
}

export async function generateInterface(request: GenerationRequest): Promise<GenerationResponse> {
  try {
    const response = await axios.post<GenerationResponse>(`${API_URL}/generate`, request, { timeout: GENERATE_TIMEOUT_MS })
    return response.data
  } catch (error) {
    // A missing backend, CORS failure, or unreachable production URL has no
    // HTTP response. Keep the client usable with the browser-only generator.
    if (axios.isAxiosError(error) && !error.response) {
      console.warn('Generate API unavailable; using local fallback generator.', error.message)
      return localFallbackResponse(request)
    }
    throw new Error(generationErrorMessage(error), { cause: error })
  }
}
