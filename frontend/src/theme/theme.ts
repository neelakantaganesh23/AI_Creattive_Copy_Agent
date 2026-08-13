/** Centralised Material UI theme implementing the design system in §4. */
import { createTheme, type ThemeOptions } from '@mui/material/styles';

export const palette = {
  sidebar: '#10183B',
  sidebarSecondary: '#18214A',
  primary: '#6548E8',
  secondary: '#8C5CF6',
  primarySoft: '#F4F1FF',
  pageBackground: '#F7F8FC',
  textPrimary: '#11182F',
  textSecondary: '#667085',
  border: '#E5E7EF',
  success: '#22A861',
  warning: '#F79009',
  error: '#D92D20',
} as const;

export const gradients = {
  primary: `linear-gradient(135deg, ${palette.primary} 0%, ${palette.secondary} 100%)`,
  sidebar: `linear-gradient(180deg, ${palette.sidebar} 0%, ${palette.sidebarSecondary} 100%)`,
  hero: `linear-gradient(160deg, ${palette.sidebar} 0%, #1B1B63 55%, ${palette.primary} 100%)`,
} as const;

const themeOptions: ThemeOptions = {
  palette: {
    mode: 'light',
    primary: { main: palette.primary, light: palette.secondary, contrastText: '#FFFFFF' },
    secondary: { main: palette.secondary, contrastText: '#FFFFFF' },
    success: { main: palette.success },
    warning: { main: palette.warning },
    error: { main: palette.error },
    background: { default: palette.pageBackground, paper: '#FFFFFF' },
    text: { primary: palette.textPrimary, secondary: palette.textSecondary },
    divider: palette.border,
  },
  shape: { borderRadius: 12 },
  typography: {
    fontFamily: "'Inter', 'DM Sans', 'Manrope', 'Segoe UI', system-ui, sans-serif",
    h1: { fontSize: '2.25rem', fontWeight: 700, letterSpacing: '-0.02em' },
    h2: { fontSize: '1.75rem', fontWeight: 700, letterSpacing: '-0.02em' },
    h3: { fontSize: '1.375rem', fontWeight: 600 },
    h4: { fontSize: '1.125rem', fontWeight: 600 },
    h5: { fontSize: '1rem', fontWeight: 600 },
    h6: { fontSize: '0.9375rem', fontWeight: 600 },
    body1: { fontSize: '0.9375rem' },
    body2: { fontSize: '0.875rem' },
    button: { textTransform: 'none', fontWeight: 600 },
  },
  breakpoints: {
    // Mobile < 768, tablet 768-1199, desktop >= 1200 (§17).
    values: { xs: 0, sm: 600, md: 768, lg: 1200, xl: 1536 },
  },
  components: {
    MuiCssBaseline: {
      styleOverrides: {
        '*': { boxSizing: 'border-box' },
        body: { backgroundColor: palette.pageBackground },
        // Honour the operating system's reduced-motion preference (§17).
        '@media (prefers-reduced-motion: reduce)': {
          '*, *::before, *::after': {
            animationDuration: '0.01ms !important',
            animationIterationCount: '1 !important',
            transitionDuration: '0.01ms !important',
            scrollBehavior: 'auto !important',
          },
        },
        ':focus-visible': {
          outline: `2px solid ${palette.primary}`,
          outlineOffset: '2px',
        },
      },
    },
    MuiPaper: {
      defaultProps: { elevation: 0 },
      styleOverrides: {
        root: { backgroundImage: 'none' },
        outlined: { border: `1px solid ${palette.border}` },
      },
    },
    MuiCard: {
      defaultProps: { elevation: 0, variant: 'outlined' },
      styleOverrides: {
        root: {
          borderRadius: 14,
          border: `1px solid ${palette.border}`,
          boxShadow: '0 1px 2px rgba(16, 24, 59, 0.04)',
        },
      },
    },
    MuiButton: {
      defaultProps: { disableElevation: true },
      styleOverrides: {
        root: { borderRadius: 10, paddingInline: 18, minHeight: 42 },
        containedPrimary: {
          background: gradients.primary,
          '&:hover': { filter: 'brightness(1.06)' },
          '&.Mui-disabled': { background: '#C7C2E8', color: '#FFFFFF' },
        },
      },
    },
    MuiTextField: { defaultProps: { size: 'small' } },
    MuiOutlinedInput: {
      styleOverrides: {
        root: { borderRadius: 10, backgroundColor: '#FFFFFF' },
      },
    },
    MuiChip: {
      styleOverrides: { root: { fontWeight: 600, borderRadius: 8 } },
    },
    MuiTableCell: {
      styleOverrides: {
        head: {
          color: palette.textSecondary,
          fontWeight: 600,
          fontSize: '0.8125rem',
          backgroundColor: '#FBFBFE',
        },
        root: { borderColor: palette.border },
      },
    },
    MuiTab: {
      styleOverrides: { root: { textTransform: 'none', fontWeight: 600, minHeight: 46 } },
    },
    MuiTooltip: {
      styleOverrides: { tooltip: { fontSize: '0.75rem', borderRadius: 8 } },
    },
  },
};

export const theme = createTheme(themeOptions);
