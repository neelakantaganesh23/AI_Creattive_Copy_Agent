import { zodResolver } from '@hookform/resolvers/zod';
import {
  Box,
  Button,
  Card,
  CardContent,
  FormControl,
  FormHelperText,
  InputLabel,
  OutlinedInput,
  ListSubheader,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
} from '@mui/material';
import { FileText, RefreshCw, Sparkles, Trash2 } from 'lucide-react';
import { useMemo } from 'react';
import { Controller, useForm } from 'react-hook-form';

import {
  BRIEF_MAX_LENGTH,
  BRIEF_MIN_LENGTH,
  campaignBriefSchema,
  type CampaignBriefFormValues,
} from '@/schemas/forms';
import type {
  AudienceSegment,
  Brand,
  Channel,
  GenerationCreatePayload,
  Product,
} from '@/types/models';
import { CHANNEL_LABELS } from '@/utils/format';

export const SAMPLE_BRIEF = `We are launching the new AeroFlex Running Shoes. The shoes are lightweight, breathable, and built for speed and comfort. The product is designed for everyday runners and athletes who want performance with modern style. AeroFlex Running Shoes are available in four colorways.

Key message: Run lighter. Go farther. Feel unstoppable.

Promote the launch with an exciting and energetic tone. Highlight comfort, durability, responsive cushioning, and modern design.`;

const LANGUAGES = ['English', 'Spanish', 'French', 'German', 'Portuguese', 'Japanese'];
const CHANNELS: Channel[] = ['email', 'mobile', 'sms'];

interface CampaignBriefFormProps {
  brands: Brand[];
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
  // Always pre-fill a ready-to-run sample brief so the form is never empty on
  // first load. The brand/segment are only pre-selected when the demo taxonomy
  // is present (they stay "no specific ..." on an unseeded database).
  const sampleProduct = products.find((item) => item.name === 'AeroFlex Running Shoes');
  const sampleSegment = segments.find((item) => item.name === 'Performance Seekers');
  return {
    brief: SAMPLE_BRIEF,
    channel: 'email',
    brandOrProduct: sampleProduct ? `product:${sampleProduct.id}` : '',
    audienceSegmentId: sampleSegment ? String(sampleSegment.id) : '',
    language: 'English',
  };
};

export const CampaignBriefForm = ({
  brands,
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
    // Selecting a product also pins its brand; selecting a brand leaves the
    // product unset, which the CTA rules fall back on.
    const [kind, rawId] = values.brandOrProduct.split(':');
    const product =
      kind === 'product' ? products.find((item) => String(item.id) === rawId) : undefined;
    const brandId =
      kind === 'brand' ? Number(rawId) : (product?.brand_id ?? null);

    onSubmit({
      brief: values.brief.trim(),
      channel: values.channel,
      brand_id: Number.isFinite(brandId) ? brandId : null,
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
                name="brandOrProduct"
                control={control}
                render={({ field }) => (
                  <FormControl fullWidth size="small">
                    <InputLabel id="product-label" shrink>
                      2. Brand / Product
                    </InputLabel>
                    <Select
                      {...field}
                      labelId="product-label"
                      displayEmpty
                      input={<OutlinedInput notched label="2. Brand / Product" />}
                    >
                      <MenuItem value="">
                        <em>No specific brand or product</em>
                      </MenuItem>
                      {products.length > 0 && <ListSubheader>Products</ListSubheader>}
                      {products.map((product) => (
                        <MenuItem key={`product-${product.id}`} value={`product:${product.id}`}>
                          {product.name}
                        </MenuItem>
                      ))}
                      {brands.length > 0 && <ListSubheader>Brands</ListSubheader>}
                      {brands.map((brand) => (
                        <MenuItem key={`brand-${brand.id}`} value={`brand:${brand.id}`}>
                          {brand.name}
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
                    <InputLabel id="segment-label" shrink>
                      4. Audience Segment
                    </InputLabel>
                    <Select
                      {...field}
                      labelId="segment-label"
                      displayEmpty
                      input={<OutlinedInput notched label="4. Audience Segment" />}
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
                    brandOrProduct: '',
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
