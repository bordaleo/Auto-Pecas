import { useEffect, useRef } from 'react';

const OTP_LENGTH = 4;

export default function OtpInput({ value, onChange, onComplete, length = OTP_LENGTH }) {
  const inputsRef = useRef([]);

  const digits = value.padEnd(length, ' ').split('').slice(0, length);

  const updateAt = (index, char) => {
    const next = digits.map((d, i) => (i === index ? char : d)).join('').replace(/ /g, '');
    onChange(next.slice(0, length));
    if (char && index < length - 1) {
      inputsRef.current[index + 1]?.focus();
    }
    if (next.length === length) {
      onComplete?.(next);
    }
  };

  const handleChange = (index, event) => {
    const raw = event.target.value.replace(/\D/g, '');
    if (!raw) {
      updateAt(index, '');
      return;
    }
    if (raw.length > 1) {
      const merged = `${value}${raw}`.replace(/\D/g, '').slice(0, length);
      onChange(merged);
      const focusIndex = Math.min(merged.length, length - 1);
      inputsRef.current[focusIndex]?.focus();
      if (merged.length === length) onComplete?.(merged);
      return;
    }
    updateAt(index, raw);
  };

  const handleKeyDown = (index, event) => {
    if (event.key === 'Backspace' && !digits[index]?.trim() && index > 0) {
      inputsRef.current[index - 1]?.focus();
    }
  };

  const handlePaste = (event) => {
    event.preventDefault();
    const pasted = event.clipboardData.getData('text').replace(/\D/g, '').slice(0, length);
    onChange(pasted);
    if (pasted.length === length) onComplete?.(pasted);
    inputsRef.current[Math.min(pasted.length, length - 1)]?.focus();
  };

  return (
    <div className="otp-inputs" onPaste={handlePaste}>
      {digits.map((digit, index) => (
        <input
          key={index}
          ref={(el) => { inputsRef.current[index] = el; }}
          type="text"
          inputMode="numeric"
          autoComplete={index === 0 ? 'one-time-code' : 'off'}
          maxLength={1}
          value={digit.trim()}
          aria-label={`Dígito ${index + 1}`}
          onChange={(e) => handleChange(index, e)}
          onKeyDown={(e) => handleKeyDown(index, e)}
        />
      ))}
    </div>
  );
}

export { OTP_LENGTH };
