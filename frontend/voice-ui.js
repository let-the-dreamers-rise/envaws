/* Ask by voice: browser speech recognition (hi-IN understands Hindi and Hinglish), answer spoken by
   Amazon Polly (neural Kajal) from the API, or by the browser's own voice when running locally. */
window.CHVoice = (() => {
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;

  function attach(form, input, onAsk) {
    if (!Recognition) return;
    const mic = document.createElement("button");
    mic.type = "button";
    mic.className = "btn mic";
    mic.setAttribute("aria-label", "Ask by voice, in Hindi or English");
    mic.title = "Ask by voice (Hindi or English)";
    mic.textContent = "🎙";
    form.insertBefore(mic, form.lastElementChild);
    let rec = null;
    mic.addEventListener("click", () => {
      if (rec) { rec.stop(); return; }
      rec = new Recognition();
      rec.lang = "hi-IN";
      rec.interimResults = true;
      let asked = false;
      mic.classList.add("listening");
      mic.textContent = "■";
      rec.onresult = (e) => {
        input.value = Array.from(e.results).map((r) => r[0].transcript).join("");
        if (!asked && e.results[e.results.length - 1].isFinal) { asked = true; rec.stop(); onAsk(input.value, true); }
      };
      rec.onerror = () => rec && rec.stop();
      rec.onend = () => { rec = null; mic.classList.remove("listening"); mic.textContent = "🎙"; };
      rec.start();
    });
  }

  function play(response) {
    if (response.audio_mp3_base64) {
      new Audio(`data:audio/mpeg;base64,${response.audio_mp3_base64}`).play().catch(() => {});
    } else if (response.answer && "speechSynthesis" in window) {
      const u = new SpeechSynthesisUtterance(response.answer);
      u.lang = /[ऀ-ॿ]/.test(response.answer) ? "hi-IN" : "en-IN";
      speechSynthesis.speak(u);
    }
  }

  return { attach, play };
})();
