'use client'

import { useEffect, useRef, useState } from 'react'
import {
  ArrowUp,
  Image as ImageIcon,
  Loader2,
  Mic,
  MicOff,
  Paperclip,
  Sparkles,
  User,
  X,
} from 'lucide-react'
import {
  InputGroup,
  InputGroupAddon,
  InputGroupButton,
  InputGroupTextarea,
} from '@/components/ui/input-group'
import { cn } from '@/lib/utils'
import { analyzeImage, Reporter } from '@/lib/api'

const suggestions = [
  'Projector in Lab 3 (Demo)',
  'PC in Lab 3 not working',
  'AC problem in Library',
  'Wi-Fi issue in Hostel Block C',
]

const ALLOWED_MIME_TYPES = ['image/jpeg', 'image/png', 'image/webp']
const MAX_IMAGE_SIZE_BYTES = 10 * 1024 * 1024 // 10MB

export function CommandInput({
  onSubmit,
  reporters,
  selectedReporterId,
  onSelectReporter,
}: {
  onSubmit: (value: string, reporterId: number) => void
  reporters: Reporter[]
  selectedReporterId: number
  onSelectReporter: (id: number) => void
}) {
  const [value, setValue] = useState('')
  const [focused, setFocused] = useState(false)
  const [isListening, setIsListening] = useState(false)
  const [statusError, setStatusError] = useState<string | null>(null)

  // Photo state
  const [selectedImage, setSelectedImage] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [isAnalyzingImage, setIsAnalyzingImage] = useState(false)
  const [detectedIssue, setDetectedIssue] = useState<string | null>(null)

  const ref = useRef<HTMLTextAreaElement>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const recognitionRef = useRef<SpeechRecognitionInstance | null>(null)

  // Clean up recognition & object URLs on unmount
  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort()
        } catch {}
        recognitionRef.current = null
      }
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl)
      }
    }
  }, [previewUrl])

  // --- Voice Handlers ---
  function toggleListening() {
    setStatusError(null)

    if (isListening) {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.stop()
        } catch {}
        recognitionRef.current = null
      }
      setIsListening(false)
      return
    }

    if (typeof window === 'undefined') return

    const SpeechRecognitionClass =
      window.SpeechRecognition || window.webkitSpeechRecognition

    if (!SpeechRecognitionClass) {
      setStatusError("Voice input isn't supported in this browser. Try Chrome or Edge.")
      return
    }

    try {
      const recognition = new SpeechRecognitionClass()
      recognition.continuous = true
      recognition.interimResults = true
      recognition.lang = 'en-IN'

      recognition.onstart = () => {
        setIsListening(true)
        setStatusError(null)
      }

      recognition.onresult = (event: SpeechRecognitionEvent) => {
        let fullTranscript = ''
        for (let i = 0; i < event.results.length; i++) {
          fullTranscript += event.results[i][0].transcript
        }
        if (fullTranscript.trim()) {
          setValue(fullTranscript)
        }
      }

      recognition.onerror = (event: SpeechRecognitionErrorEvent) => {
        if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
          setStatusError('Microphone permission was denied. Please allow microphone access and try again.')
        } else if (event.error === 'no-speech') {
          // Silent on timeout
        } else if (event.error !== 'aborted') {
          setStatusError('Voice recognition encountered an issue. Please try speaking again.')
        }
        setIsListening(false)
      }

      recognition.onend = () => {
        setIsListening(false)
        recognitionRef.current = null
      }

      recognitionRef.current = recognition
      recognition.start()
    } catch (err: any) {
      console.warn('[CommandInput] Speech recognition failed to start:', err)
      setStatusError('Could not start microphone. Please check permissions.')
      setIsListening(false)
    }
  }

  // --- Photo Handlers ---
  function handlePhotoClick() {
    setStatusError(null)
    fileInputRef.current?.click()
  }

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return

    if (!ALLOWED_MIME_TYPES.includes(file.type)) {
      setStatusError('Unsupported image format. Please select a JPEG, PNG, or WebP photo.')
      return
    }

    if (file.size > MAX_IMAGE_SIZE_BYTES) {
      setStatusError('Image file size exceeds the 10MB limit. Please choose a smaller photo.')
      return
    }

    if (previewUrl) {
      URL.revokeObjectURL(previewUrl)
    }

    const objectUrl = URL.createObjectURL(file)
    setSelectedImage(file)
    setPreviewUrl(objectUrl)
    setDetectedIssue(null)
    setStatusError(null)
  }

  function handleRemovePhoto() {
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl)
    }
    setSelectedImage(null)
    setPreviewUrl(null)
    setDetectedIssue(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  // --- Submit Handler ---
  async function submit() {
    // If voice recognition is running when user submits, stop it
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop()
      } catch {}
      recognitionRef.current = null
      setIsListening(false)
    }

    const trimmedText = value.trim()

    // If an image is selected, analyze it via backend Gemini Vision first
    if (selectedImage) {
      setIsAnalyzingImage(true)
      setStatusError(null)
      try {
        const result = await analyzeImage(selectedImage, trimmedText)
        const combinedGoal = result.combined_goal
        if (result.analysis?.issue) {
          setDetectedIssue(result.analysis.issue)
        }
        setIsAnalyzingImage(false)
        handleRemovePhoto()
        onSubmit(combinedGoal, selectedReporterId)
      } catch (err: any) {
        setIsAnalyzingImage(false)
        console.error('[CommandInput] Image analysis error:', err)
        setStatusError(err.message || 'Failed to analyze facility image. Please try again.')
      }
      return
    }

    // Text-only submission
    if (!trimmedText) return
    onSubmit(trimmedText, selectedReporterId)
  }

  const canSubmit = (value.trim().length > 0 || selectedImage !== null) && !isAnalyzingImage

  return (
    <div className="w-full">
      {/* Hidden file input for Photo button (supports camera capture on mobile) */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        accept="image/jpeg,image/png,image/webp"
        capture="environment"
        className="hidden"
      />

      {/* Reporter selection header */}
      <div className="mb-3 flex items-center justify-between px-2">
        <div className="inline-flex items-center gap-2 rounded-full border border-border/70 bg-card/60 px-3 py-1 text-xs text-muted-foreground shadow-sm">
          <User className="size-3.5 text-primary" />
          <span className="text-muted-foreground">Reporting as:</span>
          {reporters.length > 0 ? (
            <select
              value={selectedReporterId}
              onChange={(e) => onSelectReporter(Number(e.target.value))}
              className="cursor-pointer bg-transparent text-xs font-semibold text-foreground outline-none"
            >
              {reporters.map((rep) => (
                <option
                  key={rep.id}
                  value={rep.id}
                  className="bg-card text-foreground"
                >
                  {rep.name} ({rep.role})
                </option>
              ))}
            </select>
          ) : (
            <span className="font-medium text-foreground">Loading identity...</span>
          )}
        </div>
        <span className="text-[11px] text-muted-foreground/80">
          FastAPI Connected
        </span>
      </div>

      {/* glow */}
      <div className="relative">
        <div
          aria-hidden="true"
          className={cn(
            'pointer-events-none absolute -inset-x-6 -inset-y-4 rounded-[2rem] bg-primary/10 blur-2xl transition-opacity duration-500',
            focused || isListening || selectedImage ? 'opacity-100' : 'opacity-0',
          )}
        />
        <InputGroup
          className={cn(
            'relative rounded-3xl border-border/80 bg-card/80 px-2 pt-2 shadow-2xl shadow-black/40 backdrop-blur-xl transition-colors',
            (focused || isListening || selectedImage) && 'border-primary/40',
            isListening && 'ring-1 ring-high/30',
          )}
        >
          {/* Selected photo preview strip */}
          {selectedImage && previewUrl && (
            <div className="mx-3 mt-2 flex items-center justify-between gap-3 rounded-2xl border border-border/70 bg-background/60 p-2 text-xs">
              <div className="flex items-center gap-2.5 overflow-hidden">
                <img
                  src={previewUrl}
                  alt="Facility upload preview"
                  className="size-10 rounded-lg object-cover ring-1 ring-border"
                />
                <div className="flex flex-col min-w-0">
                  <span className="truncate font-medium text-foreground">
                    {selectedImage.name}
                  </span>
                  <span className="text-[11px] text-muted-foreground">
                    {(selectedImage.size / 1024).toFixed(1)} KB · Photo attached
                  </span>
                </div>
              </div>

              <div className="flex items-center gap-2">
                {detectedIssue && (
                  <span className="inline-flex items-center gap-1 rounded-full bg-primary/15 px-2.5 py-0.5 text-[11px] font-medium text-primary ring-1 ring-primary/25">
                    <Sparkles className="size-3" />
                    {detectedIssue}
                  </span>
                )}
                {isAnalyzingImage ? (
                  <span className="inline-flex items-center gap-1 text-primary text-[11px] font-medium">
                    <Loader2 className="size-3 animate-spin" />
                    Analyzing photo with Gemini Vision...
                  </span>
                ) : (
                  <button
                    type="button"
                    onClick={handleRemovePhoto}
                    className="rounded-full p-1 text-muted-foreground hover:bg-card hover:text-foreground"
                    title="Remove attached photo"
                  >
                    <X className="size-4" />
                  </button>
                )}
              </div>
            </div>
          )}

          <div className="flex items-start gap-3 px-3 pt-2">
            <span className="mt-1.5 flex size-6 items-center justify-center rounded-lg bg-primary/15 text-primary ring-1 ring-primary/25">
              <Sparkles className="size-3.5" />
            </span>
            <InputGroupTextarea
              ref={ref}
              value={value}
              onChange={(e) => setValue(e.target.value)}
              onFocus={() => setFocused(true)}
              onBlur={() => setFocused(false)}
              onKeyDown={(e) => {
                if (
                  e.key === 'Enter' &&
                  !e.shiftKey &&
                  !e.nativeEvent.isComposing &&
                  e.keyCode !== 229
                ) {
                  e.preventDefault()
                  if (canSubmit) submit()
                }
              }}
              placeholder={
                isListening
                  ? 'Listening to your voice... Speak clearly into your mic.'
                  : selectedImage
                    ? 'Optional: Describe any details about this photo (e.g. Lab 3 projector presentation tomorrow at 10 AM)'
                    : "e.g. The projector in Lab 3 isn't working. I have my project presentation tomorrow at 10 AM. Please handle it."
              }
              className="min-h-14 px-0 text-lg leading-relaxed placeholder:text-muted-foreground/70 md:text-xl"
              rows={2}
            />
          </div>
          <InputGroupAddon align="block-end" className="gap-2 px-3 pb-2">
            {/* Voice input button with active listening state */}
            {isListening ? (
              <InputGroupButton
                size="sm"
                variant="default"
                type="button"
                onClick={toggleListening}
                className="relative flex items-center gap-1.5 rounded-full bg-high/15 text-high ring-1 ring-high/30 hover:bg-high/25 animate-ai-pulse-ring"
                title="Click to stop listening"
              >
                <span className="relative flex size-2">
                  <span className="absolute inline-flex size-full animate-ping rounded-full bg-high opacity-75" />
                  <span className="relative inline-flex size-2 rounded-full bg-high" />
                </span>
                <Mic className="size-4 animate-pulse text-high" />
                <span className="text-xs font-semibold">Listening...</span>
              </InputGroupButton>
            ) : (
              <InputGroupButton
                size="sm"
                variant="ghost"
                type="button"
                onClick={toggleListening}
                className="text-muted-foreground transition-colors hover:text-foreground"
                title="Start voice input (Web Speech API)"
              >
                <Mic className="size-4" />
                Voice
              </InputGroupButton>
            )}

            {/* Photo upload button */}
            <InputGroupButton
              size="sm"
              variant={selectedImage ? 'default' : 'ghost'}
              type="button"
              onClick={handlePhotoClick}
              className={cn(
                'text-muted-foreground transition-colors hover:text-foreground',
                selectedImage && 'bg-primary/15 text-primary ring-1 ring-primary/25',
              )}
              title="Attach equipment or facility photo"
            >
              {selectedImage ? (
                <ImageIcon className="size-4 text-primary" />
              ) : (
                <Paperclip className="size-4" />
              )}
              {selectedImage ? 'Photo attached' : 'Photo'}
            </InputGroupButton>

            <InputGroupButton
              size="icon-sm"
              variant="default"
              className="ml-auto rounded-full bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-40"
              disabled={!canSubmit}
              onClick={submit}
              aria-label="Send to Campus Commander"
            >
              {isAnalyzingImage ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <ArrowUp className="size-4" />
              )}
            </InputGroupButton>
          </InputGroupAddon>
        </InputGroup>
      </div>

      {/* Graceful error notification */}
      {statusError && (
        <div className="mt-2 flex items-center justify-between rounded-xl bg-high/10 px-3.5 py-2 text-xs text-high ring-1 ring-high/20">
          <div className="flex items-center gap-2">
            <MicOff className="size-3.5 shrink-0" />
            <span>{statusError}</span>
          </div>
          <button
            type="button"
            onClick={() => setStatusError(null)}
            className="rounded p-0.5 text-high/70 hover:text-high"
            aria-label="Dismiss error"
          >
            <X className="size-3.5" />
          </button>
        </div>
      )}

      <div className="mt-5 flex flex-wrap items-center justify-center gap-2">
        {suggestions.map((s) => (
          <button
            key={s}
            type="button"
            onClick={() => {
              if (s === 'Projector in Lab 3 (Demo)') {
                setValue(
                  "The projector in Lab 3 isn't working. I have my project presentation tomorrow at 10 AM. Please handle it.",
                )
              } else if (s === 'PC in Lab 3 not working') {
                setValue("The PC in Lab 3 isn't working.")
              } else {
                setValue(s)
              }
              ref.current?.focus()
            }}
            className="rounded-full border border-border/70 bg-card/50 px-3.5 py-1.5 text-sm text-muted-foreground transition-colors hover:border-primary/40 hover:text-foreground"
          >
            {s}
          </button>
        ))}
      </div>
    </div>
  )
}
