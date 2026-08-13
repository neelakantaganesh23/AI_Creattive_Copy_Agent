import {
  Box,
  Button,
  Card,
  CardContent,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  FormControlLabel,
  IconButton,
  InputLabel,
  MenuItem,
  Select,
  Skeleton,
  Stack,
  Switch,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Tooltip,
} from '@mui/material';
import { Pencil, Plus, Trash2 } from 'lucide-react';
import { useCallback, useEffect, useState, type ReactNode } from 'react';

import { type ApiError, toApiError } from '@/api/client';
import { EmptyState } from '@/components/common/EmptyState';
import { ErrorAlert } from '@/components/common/ErrorAlert';
import { PageHeader } from '@/components/common/PageHeader';

export type FieldValue = string | number | boolean | null;

export interface FieldDefinition {
  name: string;
  label: string;
  type: 'text' | 'multiline' | 'number' | 'select' | 'switch';
  options?: Array<{ value: string; label: string }>;
  required?: boolean;
  helperText?: string;
  defaultValue?: FieldValue;
}

export interface ColumnDefinition<T> {
  key: string;
  label: string;
  render: (row: T) => ReactNode;
}

export interface ResourceManagerProps<T extends { id: number }> {
  title: string;
  description: string;
  entityName: string;
  columns: Array<ColumnDefinition<T>>;
  fields: FieldDefinition[];
  canManage: boolean;
  load: () => Promise<T[]>;
  create: (payload: Record<string, FieldValue>) => Promise<unknown>;
  update: (id: number, payload: Record<string, FieldValue>) => Promise<unknown>;
  remove: (id: number) => Promise<void>;
  toFormValues: (row: T) => Record<string, FieldValue>;
}

const emptyValues = (fields: FieldDefinition[]): Record<string, FieldValue> =>
  Object.fromEntries(
    fields.map((field) => [
      field.name,
      field.defaultValue ?? (field.type === 'switch' ? true : ''),
    ]),
  );

/**
 * Table + create/edit dialog shared by every taxonomy screen, so the CRUD
 * behaviour and permissions live in one place.
 */
export const ResourceManager = <T extends { id: number }>({
  title,
  description,
  entityName,
  columns,
  fields,
  canManage,
  load,
  create,
  update,
  remove,
  toFormValues,
}: ResourceManagerProps<T>): JSX.Element => {
  const [rows, setRows] = useState<T[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<ApiError | null>(null);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [values, setValues] = useState<Record<string, FieldValue>>(emptyValues(fields));
  const [isSaving, setIsSaving] = useState(false);
  const [reloadToken, setReloadToken] = useState(0);

  useEffect(() => {
    let cancelled = false;
    const run = async (): Promise<void> => {
      setIsLoading(true);
      setError(null);
      try {
        const data = await load();
        if (!cancelled) setRows(data);
      } catch (caught) {
        if (!cancelled) setError(toApiError(caught));
      } finally {
        if (!cancelled) setIsLoading(false);
      }
    };
    void run();
    return () => {
      cancelled = true;
    };
    // `load` is redefined per render by callers; the token drives refreshes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reloadToken]);

  const openCreate = (): void => {
    setEditingId(null);
    setValues(emptyValues(fields));
    setDialogOpen(true);
  };

  const openEdit = (row: T): void => {
    setEditingId(row.id);
    setValues({ ...emptyValues(fields), ...toFormValues(row) });
    setDialogOpen(true);
  };

  const handleSave = useCallback(async (): Promise<void> => {
    setIsSaving(true);
    setError(null);
    try {
      const payload = Object.fromEntries(
        Object.entries(values).map(([key, value]) => [key, value === '' ? null : value]),
      );
      if (editingId === null) {
        await create(payload);
      } else {
        await update(editingId, payload);
      }
      setDialogOpen(false);
      setReloadToken((token) => token + 1);
    } catch (caught) {
      setError(toApiError(caught));
    } finally {
      setIsSaving(false);
    }
  }, [create, editingId, update, values]);

  const handleDelete = useCallback(
    async (id: number): Promise<void> => {
      setError(null);
      try {
        await remove(id);
        setReloadToken((token) => token + 1);
      } catch (caught) {
        setError(toApiError(caught));
      }
    },
    [remove],
  );

  return (
    <Box>
      <PageHeader
        title={title}
        description={description}
        actions={
          canManage ? (
            <Button variant="contained" startIcon={<Plus size={16} />} onClick={openCreate}>
              New {entityName}
            </Button>
          ) : undefined
        }
      />

      <ErrorAlert error={error} onRetry={() => setReloadToken((token) => token + 1)} />

      <Card>
        <CardContent sx={{ p: { xs: 2, md: 3 } }}>
          {isLoading ? (
            <Stack spacing={1}>
              {[0, 1, 2].map((key) => (
                <Skeleton key={key} variant="rounded" height={44} />
              ))}
            </Stack>
          ) : rows.length === 0 ? (
            <EmptyState
              title={`No ${entityName.toLowerCase()}s yet`}
              description={canManage ? `Create the first ${entityName.toLowerCase()}.` : undefined}
            />
          ) : (
            <Box sx={{ overflowX: 'auto' }}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    {columns.map((column) => (
                      <TableCell key={column.key}>{column.label}</TableCell>
                    ))}
                    {canManage && <TableCell align="right">Actions</TableCell>}
                  </TableRow>
                </TableHead>
                <TableBody>
                  {rows.map((row) => (
                    <TableRow key={row.id} hover>
                      {columns.map((column) => (
                        <TableCell key={column.key}>{column.render(row)}</TableCell>
                      ))}
                      {canManage && (
                        <TableCell align="right">
                          <Tooltip title="Edit">
                            <IconButton
                              size="small"
                              aria-label={`Edit ${entityName} ${row.id}`}
                              onClick={() => openEdit(row)}
                            >
                              <Pencil size={15} />
                            </IconButton>
                          </Tooltip>
                          <Tooltip title="Delete">
                            <IconButton
                              size="small"
                              aria-label={`Delete ${entityName} ${row.id}`}
                              onClick={() => void handleDelete(row.id)}
                            >
                              <Trash2 size={15} />
                            </IconButton>
                          </Tooltip>
                        </TableCell>
                      )}
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </Box>
          )}
        </CardContent>
      </Card>

      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>
          {editingId === null ? `New ${entityName}` : `Edit ${entityName}`}
        </DialogTitle>
        <DialogContent dividers>
          <Stack spacing={2.25} sx={{ pt: 1 }}>
            {fields.map((field) => {
              const value = values[field.name];
              if (field.type === 'switch') {
                return (
                  <FormControlLabel
                    key={field.name}
                    control={
                      <Switch
                        checked={Boolean(value)}
                        onChange={(event) =>
                          setValues((current) => ({
                            ...current,
                            [field.name]: event.target.checked,
                          }))
                        }
                      />
                    }
                    label={field.label}
                  />
                );
              }
              if (field.type === 'select') {
                return (
                  <FormControl key={field.name} size="small" fullWidth>
                    <InputLabel id={`${field.name}-label`}>{field.label}</InputLabel>
                    <Select
                      labelId={`${field.name}-label`}
                      label={field.label}
                      value={value === null || value === undefined ? '' : String(value)}
                      onChange={(event) =>
                        setValues((current) => ({ ...current, [field.name]: event.target.value }))
                      }
                    >
                      {!field.required && <MenuItem value="">None</MenuItem>}
                      {(field.options ?? []).map((option) => (
                        <MenuItem key={option.value} value={option.value}>
                          {option.label}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                );
              }
              return (
                <TextField
                  key={field.name}
                  label={field.label}
                  fullWidth
                  required={field.required}
                  helperText={field.helperText}
                  multiline={field.type === 'multiline'}
                  minRows={field.type === 'multiline' ? 3 : undefined}
                  type={field.type === 'number' ? 'number' : 'text'}
                  value={value === null || value === undefined ? '' : String(value)}
                  onChange={(event) =>
                    setValues((current) => ({
                      ...current,
                      [field.name]:
                        field.type === 'number'
                          ? event.target.value === ''
                            ? ''
                            : Number(event.target.value)
                          : event.target.value,
                    }))
                  }
                />
              );
            })}
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDialogOpen(false)} color="inherit">
            Cancel
          </Button>
          <Button variant="contained" onClick={() => void handleSave()} disabled={isSaving}>
            {isSaving ? 'Saving...' : 'Save'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};
