import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import ContactoWhatsApp from './ContactoWhatsApp';

describe('ContactoWhatsApp', () => {
  it('arma el enlace wa.me con el teléfono internacional sin símbolos', () => {
    render(<ContactoWhatsApp telefono="+54 9 11 4000-0001" nombre="Juana Pérez" />);

    const enlace = screen.getByRole('link', { name: 'WhatsApp de Juana Pérez' });
    expect(enlace).toHaveAttribute('href', expect.stringContaining('https://wa.me/5491140000001'));
    expect(enlace).toHaveAttribute('target', '_blank');
    expect(enlace).toHaveAttribute('rel', expect.stringContaining('noopener'));
  });

  it('prellena el saludo con el nombre del paciente', () => {
    render(<ContactoWhatsApp telefono="+5491140000001" nombre="Juana Pérez" />);

    const href = screen.getByRole('link', { name: 'WhatsApp de Juana Pérez' }).getAttribute('href');

    expect(href).toContain('text=');
    expect(decodeURIComponent(href ?? '')).toContain('Hola Juana Pérez');
  });
});
