import { Box, Dialog, DialogContent, DialogTitle, IconButton, Typography } from '@mui/material';
import { X } from 'lucide-react';

interface PromptDialogProps {
  open: boolean;
  onClose: () => void;
  title: string;
  prompt: string | null;
}

/** Shows the full prompt sent to a model for one workflow stage. Admin-only:
 *  callers gate visibility with `hasRole('admin')` before rendering this. */
export const PromptDialog = ({ open, onClose, title, prompt }: PromptDialogProps): JSX.Element => (
  <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
    <DialogTitle sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
      <Typography variant="h6" component="span">
        Prompt: {title}
      </Typography>
      <IconButton aria-label="Close prompt" onClick={onClose} size="small">
        <X size={18} />
      </IconButton>
    </DialogTitle>
    <DialogContent dividers>
      <Box
        component="pre"
        sx={{
          m: 0,
          fontFamily: 'monospace',
          fontSize: '0.8rem',
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
          maxHeight: '60vh',
          overflow: 'auto',
        }}
      >
        {prompt ?? 'No prompt was recorded for this stage.'}
      </Box>
    </DialogContent>
  </Dialog>
);
