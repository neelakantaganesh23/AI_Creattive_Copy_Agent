import { zodResolver } from '@hookform/resolvers/zod';
import {
  Box,
  Button,
  Card,
  CardContent,
  FormControl,
  FormHelperText,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { FileText, RefreshCw, Sparkles, Trash2 } from 'lucide-react';
import { useMemo } from 'react';
import { Controller, useForm } from 'react-hook-form';

import { env } from '@/config/env';
import {
  BRIEF_MAX_LENGTH,
  BRIEF_MIN_LENGTH,
  campaignBriefSchema,
  type CampaignBriefFormValues,
} from '@/schemas/forms';
import type { AudienceSegment, Channel, GenerationCreatePayload, Product } from '@/types/models';
import { CHANNEL_LABELS } from '@/utils/format';

export const SAMPLE_BRIEF = `We are launching the new AeroFlex Running Shoes. The shoes are lightweight, breathable, and built for speed and comfort. The product is designed for everyday runners and athletes who want performance with modern style. AeroFlex Running Shoes are available in four colorways.

Key message: Run lighter. Go farther. Feel unstoppable.

Promote the launch with an exciting and energetic tone. Highlight comfort, durability, responsive cushioning, and modern design.`;

const LANGUAGES = ['English', 'Spanish', 'French', 'German', 'Portuguese', 'Japanese'];
const CHANNELS: Channel[] = ['email', 'mobile', 'sms'];

interface CampaignBriefFormProps {
  products: Product[];
  segments: AudienceSegment[];
  /** A generation is in flight; the submit button shows progress. */
  isSubmitting: boolean;
  /** The user may not generate at all (read-only role). */
  disabled?: boolean;
  canRegenerate?: boolean;
  variant?: 'full' | 'compact';
  onSubmit: (payload: GenerationCreatePayload) => void;
  onRegenerate?: () => void;
}

const defaultsFor = (
  products: Product[],
  segments: AudienceSegment[],
): CampaignBriefFormValues => {
  if (!env.enableDemoData) {
    return {
      brief: '',
      channel: 'email',
      productId: '',
      audienceSegmentId: '',
      language: 'English',
    };
  }
  // Development convenience: pre-select the documented sample campaign (§8).
  const sampleProduct = products.find((item) => item.name === 'AeroFlex Running Shoes');
  const sampleSegment = segments.find((item) => item.name === 'Performance Seekers');
  return {
    brief: SAMPLE_BRIEF,
    channel: 'email',
    productId: sampleProduct ? String(sampleProduct.id) : '',
    audienceSegmentId: sampleSegment ? String(sampleSegment.id) : '',
    language: 'English',
  };
};

export const CampaignBriefForm = ({
  products,
  segments,
  isSubmitting,
  disabled = false,
  canRegenerate = false,
  variant = 'full',
  onSubmit,
  onRegenerate,
}: CampaignBriefFormProps): JSX.Element => {
  const isLocked = isSubmitting || disabled;
  // Memoised so the form only re-syncs when the taxonomy actually loads, not on
  // every render (react-hook-form compares `values` by reference).
  const defaults = useMemo(() => defaultsFor(products, segments), [products, segments]);

  const {
    control,
    register,
    handleSubmit,
    reset,
    watch,
    formState: { errors },
  } = useForm<CampaignBriefFormValues>({
    resolver: zodResolver(campaignBriefSchema),
    defaultValues: defaults,
    values: defaults,
    resetOptions: { keepDirtyValues: true },
  });

  const brief = watch('brief') ?? '';

  const submit = (values: CampaignBriefFormValues): void => {
    const product = products.find((item) => String(item.id) === values.productId);
    onSubmit({
      brief: values.brief.trim(),
      channel: values.channel,
      brand_id: product?.brand_id ?? null,
      product_id: product?.id ?? null,
      audience_segment_id: values.audienceSegmentId ? Number(values.audienceSegmentId) : null,
      language: values.language,
    });
  };

  return (
    <Card component="section" aria-labelledby="campaign-brief-heading">
      <CardContent sx={{ p: { xs: 2, md: 3 } }}>
        <Stack direction="row" spacing={1.25} alignItems="center" sx={{ mb: 2 }}>
          <Box sx={{ color: 'primary.main', display: 'flex' }} aria-hidden>
            <FileText size={18} />
          </Box>
          <Box>
            <Typography variant="h5" component="h2" id="campaign-brief-heading">
              {variant === 'full' ? '1. Campaign Brief' : 'Campaign Brief'}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Provide the raw marketing brief or campaign information
            </Typography>
          </Box>
        </Stack>

        <Box component="form" onSubmit={handleSubmit(submit)} noValidate>
          <Stack spacing={2.25}>
            <Box>
              <TextField
                {...register('brief')}
                label="Raw Marketing Brief"
                placeholder="Enter your raw marketing brief, campaign details, key messages, product information, target audience insights..."
                multiline
                minRows={variant === 'full' ? 7 : 5}
                fullWidth
                inputProps={{ maxLength: BRIEF_MAX_LENGTH, 'aria-describedby': 'brief-counter' }}
                error={Boolean(errors.brief)}
                helperText={errors.brief?.message}
              />
              <Typography
                id="brief-counter"
                variant="caption"
                color={brief.length > BRIEF_MAX_LENGTH ? 'error' : 'text.secondary'}
                sx={{ display: 'block', textAlign: 'right', mt: 0.5 }}
              >
                {brief.length} / {BRIEF_MAX_LENGTH}
                {brief.length < BRIEF_MIN_LENGTH && brief.length > 0
                  ? ` (minimum ${BRIEF_MIN_LENGTH})`
                  : ''}
              </Typography>
            </Box>

            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
              <Controller
                name="productId"
                control={control}
                render={({ field }) => (
                  <FormControl fullWidth size="small">
                    <InputLabel id="product-label">2. Brand / Product</InputLabel>
                    <Select
                      {...field}
                      labelId="product-label"
                      label="2. Brand / Product"
                      displayEmpty
                    >
                      <MenuItem value="">
                        <em>No specific product</em>
                      </MenuItem>
                      {products.map((product) => (
                        <MenuItem key={product.id} value={String(product.id)}>
                          {product.name}
                        </MenuItem>
                      ))}
                    </Select>
                    <FormHelperText>Drives the deterministic CTA</FormHelperText>
                  </FormControl>
                )}
              />

              <Controller
                name="channel"
                control={control}
                render={({ field }) => (
                  <FormControl fullWidth size="small" error={Boolean(errors.channel)}>
                    <InputLabel id="channel-label">3. Channel</InputLabel>
                    <Select {...field} labelId="channel-label" label="3. Channel">
                      {CHANNELS.map((channel) => (
                        <MenuItem key={channel} value={channel}>
                          {CHANNEL_LABELS[channel]}
                        </MenuItem>
                      ))}
                    </Select>
                    <FormHelperText>
                      {errors.channel?.message ?? 'Primary channel for this campaign'}
                    </FormHelperText>
                  </FormControl>
                )}
              />
            </Stack>

            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2}>
              <Controller
                name="audienceSegmentId"
                control={control}
                render={({ field }) => (
                  <FormControl fullWidth size="small">
                    <InputLabel id="segment-label">4. Audience Segment</InputLabel>
                    <Select
                      {...field}
                      labelId="segment-label"
                      label="4. Audience Segment"
                      displayEmpty
                    >
                      <MenuItem value="">
                        <em>No specific segment</em>
                      </MenuItem>
                      {segments.map((segment) => (
                        <MenuItem key={segment.id} value={String(segment.id)}>
                          {segment.name}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                )}
              />

              <Controller
                name="language"
                control={control}
                render={({ field }) => (
                  <FormControl fullWidth size="small">
                    <InputLabel id="language-label">5. Language (Optional)</InputLabel>
                    <Select {...field} labelId="language-label" label="5. Language (Optional)">
                      {LANGUAGES.map((language) => (
                        <MenuItem key={language} value={language}>
                          {language}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                )}
              />
            </Stack>

            <Stack direction={{ xs: 'column', sm: 'row' }} spacing={1.5}>
              {canRegenerate && onRegenerate && (
                <Button
                  type="button"
                  variant="outlined"
                  startIcon={<RefreshCw size={16} />}
                  onClick={onRegenerate}
                  disabled={isLocked}
                >
                  Regenerate
                </Button>
              )}
              <Button
                type="button"
                variant="text"
                color="inherit"
                startIcon={<Trash2 size={16} />}
                onClick={() =>
                  reset({
                    brief: '',
                    channel: 'email',
                    productId: '',
                    audienceSegmentId: '',
                    language: 'English',
                  })
                }
                disabled={isLocked}
              >
                Clear Form
              </Button>
              <Box sx={{ flex: 1 }} />
              <Button
                type="submit"
                variant="contained"
                startIcon={<Sparkles size={16} />}
                disabled={isLocked}
                sx={{ minWidth: 170 }}
              >
                {isSubmitting ? 'Generating...' : 'Generate Copy'}
              </Button>
            </Stack>
          </Stack>
        </Box>
      </CardContent>
    </Card>
  );
};
