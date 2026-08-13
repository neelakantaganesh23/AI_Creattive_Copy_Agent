/** Clipboard and file-download helpers for generated copy. */
import type { GenerationDetail, GenerationOutput } from '@/types/models';
import { CHANNEL_LABELS, FIELD_LABELS } from '@/utils/format';

export const copyToClipboard = async (text: string): Promise<boolean> => {
  try {
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch {
    // Falls through to the manual path below.
  }
  return false;
};

export const outputToPlainText = (
  output: GenerationOutput,
  generation?: Pick<GenerationDetail, 'title' | 'audience_segment_name' | 'created_at'>,
): string => {
  const lines: string[] = [];
  if (generation) {
    lines.push(generation.title, '');
    if (generation.audience_segment_name) {
      lines.push(`Audience segment: ${generation.audience_segment_name}`);
    }
    lines.push(`Primary channel: ${CHANNEL_LABELS[output.channel]}`, `Language: ${output.language}`, '');
  }

  const sections: Array<[string, Record<string, string>]> = [
    ['EMAIL', output.email as unknown as Record<string, string>],
    ['MOBILE', output.mobile as unknown as Record<string, string>],
    ['SMS', output.sms as unknown as Record<string, string>],
  ];

  for (const [heading, payload] of sections) {
    lines.push(heading, '-'.repeat(heading.length));
    for (const [field, value] of Object.entries(payload)) {
      lines.push(`${FIELD_LABELS[field] ?? field}: ${value}`);
    }
    lines.push('');
  }

  lines.push('AI-generated content should be reviewed and validated against your brand');
  lines.push('guidelines before publishing.');
  return lines.join('\n');
};

export const downloadFile = (filename: string, contents: string, mimeType: string): void => {
  const blob = new Blob([contents], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement('a');
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
};

export const downloadAsJson = (name: string, output: GenerationOutput): void =>
  downloadFile(`${name}.json`, JSON.stringify(output, null, 2), 'application/json');

export const downloadAsText = (
  name: string,
  output: GenerationOutput,
  generation?: Pick<GenerationDetail, 'title' | 'audience_segment_name' | 'created_at'>,
): void => downloadFile(`${name}.txt`, outputToPlainText(output, generation), 'text/plain');

export const slugifyFilename = (value: string): string =>
  value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 60) || 'generated-copy';
