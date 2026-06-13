/**
 * CRM Digital FTE - Navigation Bar
 * Simple hash-based nav between pages (form, dashboard, status).
 */

function Navbar({ currentPage, onNavigate }) {
  const links = [
    { hash: 'form', label: 'Support Form' },
    { hash: 'dashboard', label: 'Dashboard' },
    { hash: 'status', label: 'Ticket Status' },
  ];

  const navItemStyle = (active) =>
    'px-4 py-2 text-sm font-medium rounded-lg transition-colors ' +
    (active
      ? 'bg-blue-600 text-white shadow-sm'
      : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800');

  return (
    <div className="border-b border-gray-800 bg-gray-900/80 backdrop-blur-sm">
      <div className="max-w-7xl mx-auto px-6 py-3 flex items-center justify-between">
        <span className="text-sm font-bold bg-gradient-to-r from-blue-400 to-green-400 bg-clip-text text-transparent">
          CRM Digital FTE
        </span>
        <nav className="flex gap-2">
          {links.map((link) => (
            <button
              key={link.hash}
              className={navItemStyle(currentPage === link.hash)}
              onClick={() => onNavigate(link.hash)}
            >
              {link.label}
            </button>
          ))}
        </nav>
      </div>
    </div>
  );
}

window.Navbar = Navbar;
