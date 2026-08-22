import { TopNav } from '@/components/top-nav'
import { StudentApp } from '@/components/student/student-app'

export default function Page() {
  return (
    <main className="campus-storm-shell min-h-screen">
      <div className="storm-atmosphere" aria-hidden="true">
        <div className="storm-aurora" />
        <div className="storm-fog" />
        <div className="storm-rain" />
        <div className="storm-particles" />
        <div className="storm-hud-grid" />
        <div className="storm-vignette" />
      </div>
      <div className="thunder-flash" aria-hidden="true" />
      <div className="thunder-lightning one" aria-hidden="true" />
      <div className="thunder-lightning two" aria-hidden="true" />
      <div className="thunder-lightning three" aria-hidden="true" />
      <TopNav />
      <StudentApp />
    </main>
  )
}
