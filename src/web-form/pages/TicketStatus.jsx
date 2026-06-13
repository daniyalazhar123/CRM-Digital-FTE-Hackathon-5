/**
 * CRM Digital FTE - Ticket Status Lookup
 * Look up a support ticket by ID and view its status and conversation history.
 */

const API_BASE = 'http://localhost:8000';

function TicketStatus() {
  const [ticketId, setTicketId] = React.useState('');
  const [ticket, setTicket] = React.useState(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState(null);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!ticketId.trim()) return;

    setLoading(true);
    setError(null);
    setTicket(null);

    try {
      const res = await fetch(`${API_BASE}/support/ticket/${ticketId.trim()}`);
      if (!res.ok) {
        if (res.status === 404) throw new Error('Ticket not found');
        throw new Error(`Request failed with status ${res.status}`);
      }
      const data = await res.json();
      setTicket(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const statusBadge = (status) => {
    const colors = {
      open: 'bg-blue-900 text-blue-300',
      resolved: 'bg-green-900 text-green-300',
      escalated: 'bg-red-900 text-red-300',
      closed: 'bg-gray-800 text-gray-400',
    };
    return colors[status] || 'bg-gray-800 text-gray-400';
  };

  const channelBadge = (channel) => {
    const colors = {
      email: 'bg-blue-900 text-blue-300',
      whatsapp: 'bg-green-900 text-green-300',
      web_form: 'bg-yellow-900 text-yellow-300',
    };
    return colors[channel] || 'bg-gray-800 text-gray-400';
  };

  return (
    <div className="min-h-screen bg-gray-950 text-gray-200">
      <div className="max-w-3xl mx-auto px-6 py-8">
        {/* Search Card */}
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 mb-8">
          <h2 className="text-lg font-bold text-gray-100 mb-2">Ticket Status</h2>
          <p className="text-sm text-gray-500 mb-6">
            Enter your ticket ID to view status and conversation history.
          </p>

          <form onSubmit={handleSubmit} className="flex gap-3">
            <input
              type="text"
              value={ticketId}
              onChange={(e) => setTicketId(e.target.value)}
              placeholder="e.g. TKT-20260613222653-5628"
              className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 
                         text-sm text-gray-200 placeholder-gray-500
                         focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              disabled={loading}
            />
            <button
              type="submit"
              disabled={loading || !ticketId.trim()}
              className="px-6 py-2.5 bg-blue-600 text-white text-sm font-medium rounded-lg
                         hover:bg-blue-700 disabled:bg-gray-700 disabled:text-gray-500
                         transition-colors"
            >
              {loading ? 'Searching...' : 'Look Up'}
            </button>
          </form>

          {error && (
            <div className="mt-4 p-3 bg-red-900/30 border border-red-800 rounded-lg text-sm text-red-300">
              {error}
            </div>
          )}
        </div>

        {/* Ticket Details */}
        {ticket && (
          <div className="space-y-6">
            {/* Status Card */}
            <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-sm font-mono text-blue-400">{ticket.ticket_id}</h3>
                <span className={'text-xs font-medium px-2.5 py-1 rounded ' + statusBadge(ticket.status)}>
                  {ticket.status}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-4 text-sm">
                <div>
                  <span className="text-gray-500">Created</span>
                  <p className="text-gray-200 mt-0.5">{new Date(ticket.created_at).toLocaleString()}</p>
                </div>
                <div>
                  <span className="text-gray-500">Last Updated</span>
                  <p className="text-gray-200 mt-0.5">{new Date(ticket.last_updated).toLocaleString()}</p>
                </div>
              </div>
            </div>

            {/* Messages */}
            {ticket.messages && ticket.messages.length > 0 && (
              <div className="bg-gray-900 border border-gray-800 rounded-xl p-6">
                <h3 className="text-xs uppercase tracking-wider text-gray-500 mb-4 pb-3 border-b border-gray-800">
                  Conversation ({ticket.messages.length} messages)
                </h3>

                <div className="space-y-4">
                  {ticket.messages.map((msg, i) => (
                    <div key={i} className="flex gap-3">
                      <div className={`flex-shrink-0 w-2 h-2 mt-2 rounded-full ${
                        msg.role === 'agent' ? 'bg-blue-500' : 'bg-gray-600'
                      }`} />
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs font-medium text-gray-400 uppercase">
                            {msg.role || 'customer'}
                          </span>
                          <span className={'text-xs px-1.5 py-0.5 rounded ' + channelBadge(msg.channel)}>
                            {msg.channel}
                          </span>
                          {msg.sentiment_score != null && (
                            <span className="text-xs text-gray-600">
                              sentiment: {msg.sentiment_score.toFixed(2)}
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-gray-300 break-words whitespace-pre-wrap">
                          {msg.content || msg.message}
                        </p>
                        {msg.created_at && (
                          <p className="text-xs text-gray-600 mt-1">
                            {new Date(msg.created_at).toLocaleString()}
                          </p>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

window.TicketStatus = TicketStatus;
