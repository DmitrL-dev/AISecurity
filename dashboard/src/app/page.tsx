export default function DashboardPage() {
  return (
    <div>
      <h1 className="text-3xl font-bold mb-8">Security Dashboard</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="card">
          <h3 className="text-sm text-gray-400 mb-2">Total Scans</h3>
          <p className="text-3xl font-bold text-emerald-500">12,847</p>
        </div>
        <div className="card">
          <h3 className="text-sm text-gray-400 mb-2">Threats Blocked</h3>
          <p className="text-3xl font-bold text-red-500">342</p>
        </div>
        <div className="card">
          <h3 className="text-sm text-gray-400 mb-2">Active Engines</h3>
          <p className="text-3xl font-bold text-blue-500">24</p>
        </div>
      </div>

      <div className="card">
        <h2 className="text-xl font-semibold mb-4">Recent Activity</h2>
        <div className="space-y-3">
          <div className="flex justify-between items-center py-2 border-b border-[#2a2a2a]">
            <span>Injection attempt blocked</span>
            <span className="status-danger">High Risk</span>
          </div>
          <div className="flex justify-between items-center py-2 border-b border-[#2a2a2a]">
            <span>PII detected in output</span>
            <span className="status-warning">Warning</span>
          </div>
          <div className="flex justify-between items-center py-2 border-b border-[#2a2a2a]">
            <span>Normal query processed</span>
            <span className="status-safe">Safe</span>
          </div>
        </div>
      </div>
    </div>
  );
}
