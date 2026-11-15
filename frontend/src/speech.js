// Text-to-speech using the browser's built-in voices (free, works offline on most phones)
const CODES = { English: 'en-IN', Hindi: 'hi-IN', Gujarati: 'gu-IN' };

export const speechSupported = () => typeof window !== 'undefined' && 'speechSynthesis' in window;

// false only when voices are loaded and none match the language
export function hasVoice(language) {
  if (!speechSupported()) return false;
  const voices = window.speechSynthesis.getVoices();
  if (voices.length === 0) return true; // not loaded yet: try anyway
  const prefix = (CODES[language] || 'en').slice(0, 2).toLowerCase();
  return voices.some((v) => v.lang.toLowerCase().startsWith(prefix));
}

// Long texts are cut up because some browsers stop reading after ~15 seconds
function chunks(text) {
  const parts = text.replace(/\s+/g, ' ').match(/[^.!?।\n]+[.!?।]?/g) || [text];
  const out = [];
  let cur = '';
  for (const p of parts) {
    if ((cur + p).length > 160 && cur) { out.push(cur.trim()); cur = ''; }
    cur += p + ' ';
  }
  if (cur.trim()) out.push(cur.trim());
  return out;
}

export function stopSpeaking() {
  if (speechSupported()) window.speechSynthesis.cancel();
}

// Returns false if it could not speak (no support / no voice for that language)
export function speak(text, language, onEnd) {
  if (!speechSupported() || !text || !hasVoice(language)) return false;
  const synth = window.speechSynthesis;
  synth.cancel();
  const list = chunks(text);
  list.forEach((c, i) => {
    const u = new SpeechSynthesisUtterance(c);
    u.lang = CODES[language] || 'en-IN';
    u.rate = 0.9; // a little slower is easier to follow
    if (i === list.length - 1 && onEnd) { u.onend = onEnd; u.onerror = onEnd; }
    synth.speak(u);
  });
  return true;
}

export function prescriptionScript(rx) {
  return [
    rx.summary,
    ...rx.medications.map((m) => `${m.name}. ${m.instructions_simple || ''}`),
    ...(rx.warnings || []),
    rx.follow_up,
  ].filter(Boolean).join(' ');
}
