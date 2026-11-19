export type TemplateId = "minimal" | "classic" | "it";
export type ResumeLanguage = "uk" | "en";

export type BlockKey =
  | "summary"
  | "experience"
  | "education"
  | "skills"
  | "languages"
  | "links";

export const DEFAULT_BLOCK_ORDER: BlockKey[] = [
  "summary",
  "experience",
  "education",
  "skills",
  "languages",
  "links",
];

export const BLOCK_LABELS_UK: Record<BlockKey, string> = {
  summary: "Про себе",
  experience: "Досвід роботи",
  education: "Освіта",
  skills: "Навички",
  languages: "Мови",
  links: "Посилання",
};

export interface ContactInfo {
  full_name: string;
  first_name: string;
  last_name: string;
  email: string;
  phone: string;
  location: string;
}

export interface ExperienceItem {
  id: string;
  company: string;
  position: string;
  start_date: string;
  end_date: string;
  is_current: boolean;
  bullets: string[];
}

export interface EducationItem {
  id: string;
  institution: string;
  degree: string;
  field_of_study: string;
  start_date: string;
  end_date: string;
  is_current: boolean;
}

export interface LanguageItem {
  name: string;
  level: string;
}

export interface LinkItem {
  label: string;
  url: string;
}

export interface ProfileData {
  contacts: ContactInfo;
  target_role: string;
  summary: string;
  desired_salary: string;
  work_format: string;
  experiences: ExperienceItem[];
  education: EducationItem[];
  skills: string[];
  languages: LanguageItem[];
  links: LinkItem[];
}

export interface User {
  id: string;
  email: string;
  is_email_verified: boolean;
  consent_accepted: boolean;
  preferred_interface_language: string;
  created_at: string;
}

export interface ProfileResponse {
  id: string;
  user_id: string;
  data: ProfileData;
  completeness_score: number;
  missing_blocks: string[];
  updated_at: string;
}

export interface ResumeResponse {
  id: string;
  user_id: string;
  title: string;
  template_id: TemplateId;
  language: ResumeLanguage;
  block_order: BlockKey[];
  data: ProfileData;
  estimated_pages: number;
  page_warning: boolean;
  updated_at: string;
}

export interface AIQuotaInfo {
  daily_limit: number;
  used_today: number;
  remaining_today: number;
  reset_at: string;
}

export interface AISuggestionsResponse {
  variants: string[];
  provider: string;
  quota: AIQuotaInfo;
  disclaimer: string;
}

export const EMPTY_PROFILE_DATA: ProfileData = {
  contacts: {
    full_name: "",
    first_name: "",
    last_name: "",
    email: "",
    phone: "",
    location: "",
  },
  target_role: "",
  summary: "",
  desired_salary: "",
  work_format: "",
  experiences: [],
  education: [],
  skills: [],
  languages: [],
  links: [],
};

export const DEMO_PROFILE_DATA: ProfileData = {
  contacts: {
    full_name: "Аріна Бадовська",
    first_name: "Аріна",
    last_name: "Бадовська",
    email: "arina.demo@example.com",
    phone: "+380 67 123 45 67",
    location: "Київ, Україна",
  },
  target_role: "Junior Python / Full-Stack Developer",
  summary:
    "Студентка ІТ-напряму з практичним досвідом розробки веб-застосунків на FastAPI та Next.js. Вмію проєктувати REST API, працювати з реляційними базами даних і доводити задачі до релізу.",
  desired_salary: "від $800",
  work_format: "Гібрид / Віддалено",
  experiences: [
    {
      id: "demo-exp-1",
      company: "DUICT Digital Lab",
      position: "Junior Web Developer (навчальний проєкт)",
      start_date: "2025-02",
      end_date: "",
      is_current: true,
      bullets: [
        "Розробила бекенд-сервіс на FastAPI з JWT-авторизацією та експортом PDF/DOCX",
        "Створила адаптивний редактор резюме на React/Next.js з попереднім переглядом",
      ],
    },
  ],
  education: [
    {
      id: "demo-edu-1",
      institution: "Державний університет інформаційно-комунікаційних технологій",
      degree: "Бакалавр",
      field_of_study: "Інформаційні технології",
      start_date: "2023-09",
      end_date: "",
      is_current: true,
    },
  ],
  skills: ["Python", "FastAPI", "TypeScript", "Next.js", "PostgreSQL", "Docker", "Git"],
  languages: [
    { name: "Українська", level: "Рідна" },
    { name: "Англійська", level: "B2 (Upper-Intermediate)" },
  ],
  links: [
    { label: "GitHub", url: "https://github.com/resumecraft-demo" },
    { label: "LinkedIn", url: "https://linkedin.com/in/resumecraft-demo" },
  ],
};
