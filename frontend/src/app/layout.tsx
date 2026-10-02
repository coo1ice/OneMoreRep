import type { Metadata } from 'next';
import { OneMoreRepApp } from '@/components/OneMoreRepApp';
import './globals.css';

export const metadata: Metadata = {
  title: 'OneMoreRep · Your consistency club',
  description: 'Log activity, earn EXP, build a streak, and keep showing up with your friends.',
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return <html lang="en"><body><OneMoreRepApp />{children}</body></html>;
}
