import { Box, Typography } from '@mui/material';
import { Sparkles } from 'lucide-react';

import { gradients } from '@/theme/theme';

interface LogoProps {
  variant?: 'light' | 'dark';
  size?: 'small' | 'medium' | 'large';
  showText?: boolean;
}

const ICON_SIZES = { small: 28, medium: 36, large: 52 } as const;

export const Logo = ({
  variant = 'dark',
  size = 'medium',
  showText = true,
}: LogoProps): JSX.Element => {
  const boxSize = ICON_SIZES[size];
  const textColor = variant === 'light' ? '#FFFFFF' : 'text.primary';

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.25 }}>
      <Box
        aria-hidden
        sx={{
          width: boxSize,
          height: boxSize,
          borderRadius: '10px',
          display: 'grid',
          placeItems: 'center',
          background: variant === 'light' ? 'rgba(255,255,255,0.14)' : gradients.primary,
          flexShrink: 0,
        }}
      >
        <Sparkles size={boxSize * 0.55} color="#FFFFFF" />
      </Box>
      {showText && (
        <Typography
          component="span"
          sx={{
            fontWeight: 700,
            lineHeight: 1.15,
            fontSize: size === 'large' ? '1.5rem' : '1rem',
            color: textColor,
          }}
        >
          AI Creative
          <Box
            component="span"
            sx={{
              display: 'block',
              color: variant === 'light' ? '#C7BDFF' : 'primary.main',
            }}
          >
            Copy Agent
          </Box>
        </Typography>
      )}
    </Box>
  );
};
