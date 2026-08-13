import { Box, Stack, Typography } from '@mui/material';

import { gradients, palette } from '@/theme/theme';
import type { EmailCopy } from '@/types/models';

interface EmailPreviewProps {
  copy: EmailCopy;
  brandName?: string | null;
}

/**
 * Illustrative rendering of the generated email. The product image is a CSS
 * illustration so nothing depends on external or copyrighted artwork (§9).
 */
export const EmailPreview = ({ copy, brandName }: EmailPreviewProps): JSX.Element => (
  <Box>
    <Typography variant="caption" color="text.secondary" sx={{ mb: 0.75, display: 'block' }}>
      Email Preview
    </Typography>

    <Box
      sx={{
        border: 1,
        borderColor: 'divider',
        borderRadius: 2,
        overflow: 'hidden',
        bgcolor: 'background.paper',
      }}
    >
      <Box sx={{ background: palette.sidebar, px: 2, py: 1.25 }}>
        <Typography
          sx={{ color: '#FFFFFF', fontWeight: 700, letterSpacing: '0.08em', fontSize: '0.8rem' }}
        >
          {(brandName ?? 'YOUR BRAND').toUpperCase()}
        </Typography>
      </Box>

      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} sx={{ p: 2.25 }}>
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography variant="h4" sx={{ lineHeight: 1.25, mb: 1 }}>
            {copy.headline}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            {copy.sub_heading}
          </Typography>
          <Box
            sx={{
              display: 'inline-block',
              background: gradients.primary,
              color: '#FFFFFF',
              px: 2,
              py: 1,
              borderRadius: 1.5,
              fontSize: '0.75rem',
              fontWeight: 700,
              letterSpacing: '0.04em',
            }}
          >
            {copy.cta}
          </Box>
        </Box>

        {/* Neutral product placeholder, drawn with CSS only. */}
        <Box
          aria-hidden
          sx={{
            width: { xs: '100%', sm: 148 },
            height: 108,
            flexShrink: 0,
            borderRadius: 2,
            background: 'linear-gradient(140deg, #E9ECF5 0%, #D7DCEC 100%)',
            position: 'relative',
            overflow: 'hidden',
          }}
        >
          <Box
            sx={{
              position: 'absolute',
              inset: '28% 12% 22% 10%',
              borderRadius: '46% 46% 30% 30% / 70% 70% 30% 30%',
              background: 'linear-gradient(120deg, #2B3358 0%, #4A5382 100%)',
            }}
          />
          <Box
            sx={{
              position: 'absolute',
              left: '10%',
              right: '12%',
              bottom: '20%',
              height: 8,
              borderRadius: 4,
              background: palette.secondary,
            }}
          />
        </Box>
      </Stack>
    </Box>

    <Typography variant="caption" color="text.secondary" sx={{ mt: 0.75, display: 'block' }}>
      * Preview is a representation and may vary in the final output.
    </Typography>
  </Box>
);
