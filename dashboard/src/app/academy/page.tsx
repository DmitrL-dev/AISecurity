'use client'

import { 
  GraduationCap, 
  BookOpen, 
  Play,
  Clock,
  CheckCircle,
  ExternalLink
} from 'lucide-react'
import Link from 'next/link'

interface Course {
  id: string
  title: string
  description: string
  lessons: number
  duration: string
  level: 'beginner' | 'intermediate' | 'advanced'
  progress: number
}

const courses: Course[] = [
  { id: '01', title: 'LLM Security Fundamentals', description: 'Understanding AI/LLM security basics, threat landscape, and OWASP LLM Top 10', lessons: 12, duration: '2h 30m', level: 'beginner', progress: 100 },
  { id: '02', title: 'Prompt Injection Deep Dive', description: 'Direct and indirect injection techniques, detection, and mitigation', lessons: 8, duration: '1h 45m', level: 'intermediate', progress: 75 },
  { id: '03', title: 'Jailbreak Attacks & Defense', description: 'DAN, Crescendo, Many-Shot attacks and how to defend against them', lessons: 10, duration: '2h', level: 'intermediate', progress: 50 },
  { id: '04', title: 'Agentic AI Security', description: 'MCP, A2A protocols, tool security, and autonomous agent risks', lessons: 15, duration: '3h', level: 'advanced', progress: 25 },
  { id: '05', title: 'RAG Security Patterns', description: 'Context poisoning, retrieval attacks, and secure RAG architecture', lessons: 6, duration: '1h 15m', level: 'advanced', progress: 0 },
  { id: '06', title: 'SENTINEL Integration', description: 'Integrating SENTINEL engines into your LLM applications', lessons: 8, duration: '1h 30m', level: 'intermediate', progress: 0 },
]

const levelConfig = {
  beginner: 'bg-green-500/20 text-green-400',
  intermediate: 'bg-yellow-500/20 text-yellow-400',
  advanced: 'bg-red-500/20 text-red-400',
}

export default function AcademyPage() {
  const completedCourses = courses.filter(c => c.progress === 100).length
  const inProgressCourses = courses.filter(c => c.progress > 0 && c.progress < 100).length

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-2">
            <GraduationCap className="w-7 h-7 text-cyan-400" />
            Security Academy
          </h1>
          <p className="text-gray-400 text-sm">Learn AI security from fundamentals to advanced techniques</p>
        </div>
        <Link 
          href="/docs/academy"
          className="flex items-center gap-2 px-4 py-2 border border-[#374151] rounded-lg hover:border-cyan-500 transition-colors"
        >
          <ExternalLink className="w-4 h-4" />
          Full Documentation
        </Link>
      </div>

      {/* Progress Stats */}
      <div className="grid grid-cols-3 gap-4">
        <div className="bg-[#1a1f2e] rounded-xl border border-[#374151] p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-cyan-500/20">
              <BookOpen className="w-5 h-5 text-cyan-400" />
            </div>
            <div>
              <p className="text-2xl font-bold">{courses.length}</p>
              <p className="text-sm text-gray-400">Total Courses</p>
            </div>
          </div>
        </div>
        <div className="bg-[#1a1f2e] rounded-xl border border-[#374151] p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-yellow-500/20">
              <Clock className="w-5 h-5 text-yellow-400" />
            </div>
            <div>
              <p className="text-2xl font-bold">{inProgressCourses}</p>
              <p className="text-sm text-gray-400">In Progress</p>
            </div>
          </div>
        </div>
        <div className="bg-[#1a1f2e] rounded-xl border border-[#374151] p-4">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-green-500/20">
              <CheckCircle className="w-5 h-5 text-green-400" />
            </div>
            <div>
              <p className="text-2xl font-bold">{completedCourses}</p>
              <p className="text-sm text-gray-400">Completed</p>
            </div>
          </div>
        </div>
      </div>

      {/* Courses Grid */}
      <div className="grid grid-cols-2 gap-4">
        {courses.map((course) => (
          <div 
            key={course.id}
            className="bg-[#1a1f2e] rounded-xl border border-[#374151] p-5 hover:border-cyan-500/50 transition-all cursor-pointer group"
          >
            <div className="flex justify-between items-start mb-3">
              <div>
                <span className="text-xs text-gray-500">Course {course.id}</span>
                <h3 className="font-semibold text-lg">{course.title}</h3>
              </div>
              <span className={`px-2 py-1 rounded text-xs font-medium ${levelConfig[course.level]}`}>
                {course.level}
              </span>
            </div>
            
            <p className="text-sm text-gray-400 mb-4">{course.description}</p>
            
            <div className="flex items-center gap-4 text-sm text-gray-400 mb-4">
              <span className="flex items-center gap-1">
                <BookOpen className="w-4 h-4" />
                {course.lessons} lessons
              </span>
              <span className="flex items-center gap-1">
                <Clock className="w-4 h-4" />
                {course.duration}
              </span>
            </div>
            
            {/* Progress Bar */}
            <div className="mb-3">
              <div className="flex justify-between text-xs mb-1">
                <span className="text-gray-400">Progress</span>
                <span className={course.progress === 100 ? 'text-green-400' : 'text-cyan-400'}>{course.progress}%</span>
              </div>
              <div className="h-2 bg-[#111827] rounded-full overflow-hidden">
                <div 
                  className={`h-full transition-all ${course.progress === 100 ? 'bg-green-500' : 'bg-cyan-500'}`}
                  style={{ width: `${course.progress}%` }}
                />
              </div>
            </div>
            
            <button className="w-full flex items-center justify-center gap-2 py-2 rounded-lg border border-[#374151] group-hover:border-cyan-500 group-hover:bg-cyan-500/10 transition-all">
              {course.progress === 0 ? (
                <>
                  <Play className="w-4 h-4" />
                  Start Course
                </>
              ) : course.progress === 100 ? (
                <>
                  <CheckCircle className="w-4 h-4 text-green-400" />
                  Review
                </>
              ) : (
                <>
                  <Play className="w-4 h-4" />
                  Continue
                </>
              )}
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}
