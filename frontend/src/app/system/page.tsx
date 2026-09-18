import ControlPanel from "@/components/ControlPanel";

export default function SystemPage() {
  return (
    <div className="animate-fade-in">
      <div className="flex justify-between items-center mb-8">
        <div>
          <h1 className="text-gradient" style={{ fontSize: '36px', marginBottom: '8px' }}>System Configuration</h1>
          <p className="text-muted">Manage background tasks, agent configurations, and system simulations.</p>
        </div>
      </div>
      
      <ControlPanel />
    </div>
  );
}
