import { ProfileData } from "./types";

const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;
const PHONE_RE = /^\+?[0-9\s\-()]{7,20}$/;

export function validateProfileData(data: ProfileData): string[] {
  const errors: string[] = [];

  if (data.contacts.email.trim() && !EMAIL_RE.test(data.contacts.email.trim())) {
    errors.push("Некоректний формат email у контактах.");
  }

  if (data.contacts.phone.trim()) {
    const digits = data.contacts.phone.replace(/\D/g, "");
    if (!PHONE_RE.test(data.contacts.phone.trim()) || digits.length < 7 || digits.length > 15) {
      errors.push("Некоректний формат телефону (приклад: +380501234567).");
    }
  }

  if (data.experiences.length > 15) {
    errors.push("Максимум 15 місць роботи.");
  }

  data.experiences.forEach((exp, idx) => {
    if (!exp.is_current && exp.start_date && exp.end_date && exp.end_date < exp.start_date) {
      errors.push(`Досвід #${idx + 1}: дата завершення не може бути раніше дати початку.`);
    }
  });

  data.education.forEach((edu, idx) => {
    if (!edu.is_current && edu.start_date && edu.end_date && edu.end_date < edu.start_date) {
      errors.push(`Освіта #${idx + 1}: дата завершення не може бути раніше дати початку.`);
    }
  });

  const nonEmptySkills = data.skills.filter((s) => s.trim().length > 0);
  if (nonEmptySkills.length > 30) {
    errors.push("Максимум 30 навичок.");
  }

  return errors;
}
