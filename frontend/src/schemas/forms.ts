/** Zod schemas backing the React Hook Form validation. */
import { z } from 'zod';

export const BRIEF_MIN_LENGTH = 20;
export const BRIEF_MAX_LENGTH = 4000;

export const loginSchema = z.object({
  email: z
    .string()
    .min(1, 'Email address is required.')
    .email('Enter a valid email address.'),
  password: z.string().min(1, 'Password is required.'),
  rememberMe: z.boolean().default(true),
});

export type LoginFormValues = z.infer<typeof loginSchema>;

export const registerSchema = z
  .object({
    name: z.string().min(2, 'Enter your full name.').max(120, 'Name is too long.'),
    email: z.string().min(1, 'Email address is required.').email('Enter a valid email address.'),
    password: z
      .string()
      .min(8, 'Use at least 8 characters.')
      .max(72, 'Use at most 72 characters.')
      .refine((value) => /[A-Za-z]/.test(value) && /\d/.test(value), {
        message: 'Include at least one letter and one number.',
      }),
    confirmPassword: z.string(),
  })
  .refine((values) => values.password === values.confirmPassword, {
    message: 'Passwords do not match.',
    path: ['confirmPassword'],
  });

export type RegisterFormValues = z.infer<typeof registerSchema>;

export const campaignBriefSchema = z.object({
  brief: z
    .string()
    .trim()
    .min(BRIEF_MIN_LENGTH, `The brief must be at least ${BRIEF_MIN_LENGTH} characters.`)
    .max(BRIEF_MAX_LENGTH, `The brief must be at most ${BRIEF_MAX_LENGTH} characters.`),
  channel: z.enum(['email', 'mobile', 'sms'], {
    errorMap: () => ({ message: 'Select a channel.' }),
  }),
  productId: z.string().default(''),
  audienceSegmentId: z.string().default(''),
  language: z.string().default('English'),
});

export type CampaignBriefFormValues = z.infer<typeof campaignBriefSchema>;
