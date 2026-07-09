import { NextResponse } from 'next/server'
import type { NextRequest } from 'next/server'

const GUEST_ONLY_ROUTES = ['/login', '/register']

export function proxy(request: NextRequest) {
  const hasToken = request.cookies.has('access_token')
  const { pathname } = request.nextUrl

  const isGuestRoute = GUEST_ONLY_ROUTES.includes(pathname)

  // 1. Redirect unauthenticated users to /login
  if (!hasToken && !isGuestRoute) {
    return NextResponse.redirect(new URL('/login', request.url))
  }

  // 2. Redirect authenticated users away from guest pages (like login/register) to home
  if (hasToken && isGuestRoute) {
    return NextResponse.redirect(new URL('/', request.url))
  }

  return NextResponse.next()
}

export const config = {
  matcher: [
    /*
     * Match all paths except:
     * - api (API routes)
     * - _next/static (static files)
     * - _next/image (image optimization files)
     * - favicon.ico, next.svg, vercel.svg (assets)
     * - Any path containing a dot (representing files with extensions)
     */
    '/((?!api|_next/static|_next/image|favicon.ico|next.svg|vercel.svg|.*\\..*$).*)',
  ],
}
