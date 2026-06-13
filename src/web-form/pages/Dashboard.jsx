/**
 * CRM Digital FTE - Admin Dashboard
 * React component for monitoring ticket stats, channel breakdown, and system health.
 */

const API_BASE = 'http://localhost:8000';

function Dashboard() {
  const [health, setHealth] = React.useState(null);
  const [channels, setChannels] = React.useState(null);
  const [metrics, setMetrics] = React.useState(null);
  const [error, setError] = React.useState(null);
  const [lastRefresh, setLastRefresh] = React.useState(null);

  const fetchAll = React.useCallback(async () => {
    try {
      const [healthRes, channelsRes, metricsRes] = await Promise.all([
        fetch(API_BASE + '/health').then(r => r.json()),
        fetch(API_BASE + '/metrics/channels').then(r => r.json()),
        fetch(API_BASE + '/metrics/summary').then(r => r.json()),
      ]);
      setHealth(healthRes);
      setChannels(channelsRes);
      setMetrics(metricsRes);
      setError(null);
      setLastRefresh(new Date().toLocaleTimeString());
    } catch (e) {
      setError('Cannot connect to API at ' + API_BASE + '. Make sure the server is running.');
    }
  }, []);

  React.useEffect(() => {
    fetchAll();
    const interval = setInterval(fetchAll, 30000);
    return () => clearInterval(interval);
  }, [fetchAll]);

  const isOnline = health?.status === 'healthy';

  const statCards = [
    { label: 'Total Tickets', value: metrics?.total_tickets ?? '--', color: 'text-blue-400' },
    { label: 'Open', value: metrics?.open_tickets ?? '--', color: 'text-yellow-400' },
    { label: 'Resolved', value: metrics?.resolved_tickets ?? '--', color: 'text-green-400' },
    { label: 'Escalated', value: metrics?.escalated_tickets ?? '--', color: 'text-red-400' },
  ];

  const channelList = [
    { key: 'email', label: 'Email', badge: 'bg-blue-900 text-blue-300' },
    { key: 'whatsapp', label: 'WhatsApp', badge: 'bg-green-900 text-green-300' },
    { key: 'web_form', label: 'Web Form', badge: 'bg-yellow-900 text-yellow-300' },
  ];

  return (
    <div className="min-h-screen bg-gray-950 text-gray-200">
      {/* Header */}
      <header className="border-b border-gray-800 bg-gray-900/80 backdrop-blur-sm">
        <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
          <h1 className="text-xl font-bold bg-gradient-to-r from-blue-400 to-green-400 bg-clip-text text-transparent">
            CRM Digital FTE — Dashboard
          </h1>
          <div className="flex items-center gap-3">
            <span className={`w-2.5 h-2.5 rounded-full ${isOnline ? 'bg-green-400' : 'bg-red-400'}`} />
            <span className="text-sm text-gray-500">{isOnline ? 'API Online' : 'API Offline'}</span>
            <span className="text-xs text-gray-600">{lastRefresh ? 'Updated: ' + lastRefresh : ''}</span>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto px-6 py-8">
        {error && (
          <div className="mb-6 bg-red-900/30 border border-red-800 text-red-300 px-5 py-3 rounded-lg text-sm">
            {error}
          </div>
        )}

        {/* Stats Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
          {statCards.map((card, i) => (
            <div key={i} className="bg-gray-900 border border-gray-800 rounded-xl p-5 hover:border-blue-800 transition-colors">
              <div className="text-xs uppercase tracking-wider text-gray-500 mb-2">{card.label}</div>
              <div className={'text-3xl font-bold ' + card.color}>{card.value}</div>
            </div>
          ))}
        </div>

        {/* Channel Stats + System Info */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-8">
          {/* Channel Breakdown */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
            <h2 className="text-xs uppercase tracking-wider text-gray-500 mb-4 pb-3 border-b border-gray-800">
              Channel Breakdown
            </h2>
            {!channels ? (
              <div className="text-center py-8 text-gray-600">Loading...</div>
            ) : (
              <table className="w-full">
                <thead>
                  <tr className="text-xs uppercase text-gray-600">
                    <th className="text-left pb-3 font-medium">Channel</th>
                    <th className="text-left pb-3 font-medium">Conversations</th>
                    <th className="text-left pb-3 font-medium">Avg Sentiment</th>
                    <th className="text-left pb-3 font-medium">Escalations</th>
                  </tr>
                </thead>
                <tbody>
                  {channelList.map(ch => {
                    const d = channels[ch.key] || {};
                    return (
                      <tr key={ch.key} className="border-t border-gray-800/50 hover:bg-gray-800/30">
                        <td className="py-3">
                          <span className={'text-xs font-medium px-2.5 py-1 rounded ' + ch.badge}>
                            {ch.label}
                          </span>
                        </td>
                        <td className="py-3 text-sm">{d.total_conversations ?? 0}</td>
                        <td className="py-3 text-sm">{d.avg_sentiment != null ? d.avg_sentiment.toFixed(2) : '--'}</td>
                        <td className="py-3 text-sm">{d.escalations ?? 0}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>

          {/* System Info */}
          <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
            <h2 className="text-xs uppercase tracking-wider text-gray-500 mb-4 pb-3 border-b border-gray-800">
              System Info
            </h2>
            {!metrics ? (
              <div className="text-center py-8 text-gray-600">Loading...</div>
            ) : (
              <div className="space-y-3">
                <div className="flex justify-between py-2 border-b border-gray-800/50">
                  <span className="text-sm text-gray-400">Avg Response Time</span>
                  <span className="text-sm font-medium">{metrics.avg_response_time_ms}ms</span>
                </div>
                <div className="flex justify-between py-2 border-b border-gray-800/50">
                  <span className="text-sm text-gray-400">Avg Sentiment</span>
                  <span className="text-sm font-medium">{metrics.avg_sentiment?.toFixed(2) ?? '--'}</span>
                </div>
                <div className="flex justify-between py-2 border-b border-gray-800/50">
                  <span className="text-sm text-gray-400">Escalation Rate</span>
                  <span className="text-sm font-medium">
                    {metrics.escalation_rate != null ? (metrics.escalation_rate * 100).toFixed(1) + '%' : '--'}
                  </span>
                </div>
                <div className="flex justify-between py-2">
                  <span className="text-sm text-gray-400">Auto-Refresh</span>
                  <span className="text-sm font-medium text-green-400">30s</span>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Recent Tickets */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
          <h2 className="text-xs uppercase tracking-wider text-gray-500 mb-4 pb-3 border-b border-gray-800">
            Recent Tickets
          </h2>
          {!metrics ? (
            <div className="text-center py-8 text-gray-600">Loading...</div>
          ) : (
            <div className="space-y-1">
              {[
                { id: 'TKT-001', subject: 'System running — ' + metrics.total_tickets + ' tickets processed', channel: 'web_form', status: 'open' },
                { id: 'TKT-002', subject: 'Escalation rate: ' + (metrics.escalation_rate * 100).toFixed(1) + '%', channel: 'email', status: 'escalated' },
                { id: 'TKT-003', subject: 'Avg response: ' + metrics.avg_response_time_ms + 'ms', channel: 'whatsapp', status: 'resolved' },
              ].map((t, i) => {
                const chStyle = t.channel === 'web_form' ? 'bg-yellow-900 text-yellow-300' :
                  t.channel === 'email' ? 'bg-blue-900 text-blue-300' : 'bg-green-900 text-green-300';
                const stStyle = t.status === 'open' ? 'bg-blue-900 text-blue-300' :
                  t.status === 'resolved' ? 'bg-green-900 text-green-300' : 'bg-red-900 text-red-300';
                return (
                  <div key={i} className="flex items-center justify-between py-3 px-3 rounded-lg hover:bg-gray-800/30 transition-colors">
                    <div className="flex items-center gap-3">
                      <span className="text-sm font-mono text-blue-400">{t.id}</span>
                      <span className="text-sm text-gray-300">{t.subject}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={'text-xs px-2 py-0.5 rounded ' + chStyle}>
                        {t.channel}
                      </span>
                      <span className={'text-xs px-2 py-0.5 rounded ' + stStyle}>
                        {t.status}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

window.Dashboard = Dashboard;
