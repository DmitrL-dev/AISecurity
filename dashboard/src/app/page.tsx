import { MetricsBar } from '@/components/MetricsBar'
import { HexNetwork } from '@/components/HexNetwork'
import { SunburstChart } from '@/components/SunburstChart'
import { AIAssistant } from '@/components/AIAssistant'
import { ThreatMetrics } from '@/components/ThreatMetrics'
import { LiveActivity } from '@/components/LiveActivity'

export default function DashboardPage() {
  return (
    <div className="space-y-4 lg:space-y-6">
      {/* Metrics Bar */}
      <MetricsBar />
      
      {/* Main Content Grid - stacks on mobile */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 lg:gap-6">
        {/* Left: Hex Network (2 columns on desktop) */}
        <div className="lg:col-span-2 order-2 lg:order-1">
          <HexNetwork />
        </div>
        
        {/* Right: AI Assistant */}
        <div className="lg:col-span-1 order-1 lg:order-2">
          <AIAssistant />
        </div>
      </div>

      {/* Real-time Analytics Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 lg:gap-6">
        <ThreatMetrics />
        <LiveActivity />
      </div>
      
      {/* Bottom: Sunburst Chart */}
      <SunburstChart />
    </div>
  )
}

