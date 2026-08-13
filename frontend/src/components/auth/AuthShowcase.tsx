import { Box, Stack, Typography } from '@mui/material';
import { Megaphone, Sparkles, Users } from 'lucide-react';
import type { LucideIcon } from 'lucide-react';

import { Logo } from '@/components/common/Logo';
import { gradients } from '@/theme/theme';

interface Feature {
  icon: LucideIcon;
  title: string;
  description: string;
}

const FEATURES: Feature[] = [
  {
    icon: Users,
    title: 'Audience-Focused',
    description: 'Create personalized copy that resonates with every audience segment.',
  },
  {
    icon: Megaphone,
    title: 'Multi-Channel Support',
    description: 'Generate content for Email, Mobile, and SMS effortlessly.',
  },
  {
    icon: Sparkles,
    title: 'AI-Grounded & Unique',
    description: 'Real-world insights, repetition checks, and CTA optimization built in.',
  },
];

/**
 * Marketing panel shown beside the sign-in card. Hidden below 1200px so the form
 * comes first on tablet and mobile (§5).
 */
export const AuthShowcase = (): JSX.Element => (
  <Box
    sx={{
      display: { xs: 'none', lg: 'flex' },
      flexDirection: 'column',
      justifyContent: 'center',
      width: '46%',
      maxWidth: 640,
      px: 7,
      py: 6,
      color: '#FFFFFF',
      background: gradients.hero,
      position: 'relative',
      overflow: 'hidden',
    }}
  >
    {/* Decorative wave, drawn in CSS so no external image is needed. */}
    <Box
      aria-hidden
      sx={{
        position: 'absolute',
        inset: 0,
        opacity: 0.35,
        background:
          'radial-gradient(60% 40% at 20% 12%, rgba(140,92,246,0.55) 0%, transparent 60%),' +
          'radial-gradient(50% 35% at 88% 82%, rgba(101,72,232,0.6) 0%, transparent 65%)',
      }}
    />
    <Box
      aria-hidden
      sx={{
        position: 'absolute',
        left: 0,
        right: 0,
        bottom: -40,
        height: 220,
        opacity: 0.25,
        background:
          'repeating-linear-gradient(115deg, transparent 0 22px, rgba(255,255,255,0.35) 22px 23px)',
        maskImage: 'radial-gradient(70% 100% at 30% 100%, #000 0%, transparent 75%)',
        WebkitMaskImage: 'radial-gradient(70% 100% at 30% 100%, #000 0%, transparent 75%)',
      }}
    />

    <Stack spacing={4} sx={{ position: 'relative' }}>
      <Logo variant="light" size="large" />

      <Box>
        <Typography variant="h1" sx={{ fontSize: '2rem', lineHeight: 1.25, mb: 1.5 }}>
          AI-Powered Marketing Copy
          <br />
          That Connects and Converts
        </Typography>
        <Typography sx={{ color: 'rgba(255,255,255,0.78)', maxWidth: 440 }}>
          Generate channel-ready, audience-specific marketing content in seconds with our
          multi-agent AI platform.
        </Typography>
      </Box>

      <Stack spacing={2.5}>
        {FEATURES.map(({ icon: Icon, title, description }) => (
          <Stack key={title} direction="row" spacing={2} alignItems="flex-start">
            <Box
              aria-hidden
              sx={{
                width: 44,
                height: 44,
                borderRadius: 2,
                display: 'grid',
                placeItems: 'center',
                bgcolor: 'rgba(255,255,255,0.12)',
                flexShrink: 0,
              }}
            >
              <Icon size={20} />
            </Box>
            <Box>
              <Typography sx={{ fontWeight: 600 }}>{title}</Typography>
              <Typography variant="body2" sx={{ color: 'rgba(255,255,255,0.72)' }}>
                {description}
              </Typography>
            </Box>
          </Stack>
        ))}
      </Stack>
    </Stack>
  </Box>
);
