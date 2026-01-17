export default function SettingsPage() {
  return (
    <div>
      <h1 className="text-3xl font-bold mb-8">Settings</h1>

      <div className="card mb-6">
        <h2 className="text-xl font-semibold mb-4">Security Profile</h2>
        <div className="space-y-4">
          <div>
            <label className="block text-gray-400 mb-2">Detection Profile</label>
            <select className="w-full bg-[#111] border border-[#2a2a2a] rounded-lg p-3 text-white">
              <option value="lite">Lite (Fast)</option>
              <option value="standard" selected>Standard (Balanced)</option>
              <option value="enterprise">Enterprise (Maximum)</option>
            </select>
          </div>
          <div>
            <label className="block text-gray-400 mb-2">Block Threshold</label>
            <input
              type="range"
              min="0"
              max="100"
              defaultValue="70"
              className="w-full"
            />
            <div className="flex justify-between text-sm text-gray-500">
              <span>Permissive (0)</span>
              <span>Strict (100)</span>
            </div>
          </div>
        </div>
      </div>

      <div className="card mb-6">
        <h2 className="text-xl font-semibold mb-4">API Configuration</h2>
        <div className="space-y-4">
          <div>
            <label className="block text-gray-400 mb-2">Brain API URL</label>
            <input
              type="text"
              defaultValue="http://localhost:8000"
              className="w-full bg-[#111] border border-[#2a2a2a] rounded-lg p-3 text-white"
            />
          </div>
          <div>
            <label className="block text-gray-400 mb-2">API Key</label>
            <input
              type="password"
              placeholder="sk-..."
              className="w-full bg-[#111] border border-[#2a2a2a] rounded-lg p-3 text-white"
            />
          </div>
        </div>
      </div>

      <button className="btn-primary">Save Settings</button>
    </div>
  );
}
