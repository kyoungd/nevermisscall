import { redirect } from 'next/navigation'

export default function HomePage() {
  // Redirect to dashboard for authenticated users, or to login for non-authenticated
  redirect('/login')
}