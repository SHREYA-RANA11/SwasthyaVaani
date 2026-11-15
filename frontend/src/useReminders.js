import { useEffect, useRef } from 'react';
import { speak } from './speech';

// Fires a browser notification (and optionally speaks) once for each dose that is due.
// Works while the app is open in a tab or installed on the phone.
export function useReminders({ doses, speakAloud, language }) {
  const done = useRef(new Set());
  useEffect(() => {
    if (!doses) return;
    for (const d of doses) {
      if (d.status !== 'due') continue;
      const id = `${d.scheduled_date}|${d.medication_id}|${d.scheduled_time}`;
      if (done.current.has(id)) continue;
      done.current.add(id);
      if ('Notification' in window && Notification.permission === 'granted') {
        new Notification(`💊 ${d.medication_name}`, {
          body: [d.dose, d.instructions].filter(Boolean).join(' — '),
          tag: id,
        });
      }
      if (speakAloud) speak(`${d.medication_name}. ${d.instructions || ''}`, language);
    }
  }, [doses, speakAloud, language]);
}
