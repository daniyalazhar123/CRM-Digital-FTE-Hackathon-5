/**
 * CRM Digital FTE - Web Support Form
 * Phase 2: Specialization — Step 6 (REQUIRED Deliverable)
 * 
 * A standalone React component for customer support submissions.
 * Can be embedded in any website or used with Next.js.
 * 
 * @version 1.0.0
 * @author TechCorp AI Team
 */

// =============================================================================
// CONFIGURATION
// =============================================================================

const API_BASE_URL = 'http://localhost:8000';
const API_ENDPOINT = `${API_BASE_URL}/support/submit`;
const FORM_VERSION = '1.0';

// Form categories matching backend validation
const CATEGORIES = [
  { value: 'how-to', label: 'How-To Question', icon: '❓' },
  { value: 'technical', label: 'Technical Support', icon: '🔧' },
  { value: 'billing', label: 'Billing Inquiry', icon: '💳' },
  { value: 'bug-report', label: 'Bug Report', icon: '🐛' },
  { value: 'other', label: 'Other', icon: '📝' }
];

const PRIORITIES = [
  { value: 'low', label: 'Low - Not urgent', color: 'green' },
  { value: 'medium', label: 'Medium - Need help soon', color: 'yellow' },
  { value: 'high', label: 'High - Urgent issue', color: 'red' }
];

// Validation rules
const VALIDATION_RULES = {
  name: {
    minLength: 2,
    required: true,
    errorMessage: 'Name must be at least 2 characters'
  },
  email: {
    pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
    required: true,
    errorMessage: 'Please enter a valid email address'
  },
  subject: {
    minLength: 5,
    required: true,
    errorMessage: 'Subject must be at least 5 characters'
  },
  message: {
    minLength: 10,
    maxLength: 1000,
    required: true,
    errorMessage: 'Message must be between 10 and 1000 characters'
  }
};

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

/**
 * Validate email format
 */
function isValidEmail(email) {
  const re = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return re.test(email);
}

/**
 * Validate form field
 */
function validateField(name, value) {
  const rules = VALIDATION_RULES[name];
  if (!rules) return { valid: true, error: '' };

  if (!value && rules.required) {
    return { valid: false, error: 'This field is required' };
  }

  if (value && rules.minLength && value.length < rules.minLength) {
    return { valid: false, error: `Must be at least ${rules.minLength} characters` };
  }

  if (value && rules.maxLength && value.length > rules.maxLength) {
    return { valid: false, error: `Must be no more than ${rules.maxLength} characters` };
  }

  if (value && rules.pattern && !rules.pattern.test(value)) {
    return { valid: false, error: rules.errorMessage };
  }

  return { valid: true, error: '' };
}

// =============================================================================
// ICON COMPONENTS
// =============================================================================

const LoadingSpinner = () => (
  <svg className="animate-spin -ml-1 mr-3 h-5 w-5 text-white" 
       xmlns="http://www.w3.org/2000/svg" 
       fill="none" 
       viewBox="0 0 24 24">
    <circle className="opacity-25" cx="12" cy="12" r="10" 
            stroke="currentColor" strokeWidth="4"></circle>
    <path className="opacity-75" fill="currentColor" 
          d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z">
    </path>
  </svg>
);

const CheckCircleIcon = () => (
  <svg className="w-16 h-16 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
          d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

const ErrorIcon = () => (
  <svg className="w-12 h-12 text-red-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} 
          d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
  </svg>
);

// =============================================================================
// MAIN COMPONENT
// =============================================================================

function SupportForm({ 
  apiEndpoint = API_ENDPOINT,
  onSuccess,
  onError 
}) {
  // Form state
  const [formData, setFormData] = React.useState({
    name: '',
    email: '',
    subject: '',
    category: 'how-to',
    priority: 'medium',
    message: ''
  });

  // UI state
  const [status, setStatus] = React.useState('idle'); // idle, submitting, success, error
  const [ticketId, setTicketId] = React.useState(null);
  const [error, setError] = React.useState(null);
  const [validationErrors, setValidationErrors] = React.useState({});
  const [touched, setTouched] = React.useState({});

  // Computed
  const characterCount = formData.message.length;
  const isFormValid = React.useMemo(() => {
    return (
      formData.name.length >= 2 &&
      isValidEmail(formData.email) &&
      formData.subject.length >= 5 &&
      formData.message.length >= 10 &&
      formData.message.length <= 1000 &&
      !Object.values(validationErrors).some(err => err)
    );
  }, [formData, validationErrors]);

  // Handle field change
  const handleChange = (e) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));

    // Validate on change
    const validation = validateField(name, value);
    setValidationErrors(prev => ({ ...prev, [name]: validation.error }));
  };

  // Handle field blur
  const handleBlur = (e) => {
    const { name } = e.target;
    setTouched(prev => ({ ...prev, [name]: true }));
    
    // Validate on blur
    const validation = validateField(name, formData[name]);
    setValidationErrors(prev => ({ ...prev, [name]: validation.error }));
  };

  // Validate entire form
  const validateForm = () => {
    const errors = {};
    let isValid = true;

    // Validate name
    const nameValidation = validateField('name', formData.name);
    if (!nameValidation.valid) {
      errors.name = nameValidation.error;
      isValid = false;
    }

    // Validate email
    const emailValidation = validateField('email', formData.email);
    if (!emailValidation.valid) {
      errors.email = emailValidation.error;
      isValid = false;
    }

    // Validate subject
    const subjectValidation = validateField('subject', formData.subject);
    if (!subjectValidation.valid) {
      errors.subject = subjectValidation.error;
      isValid = false;
    }

    // Validate message
    const messageValidation = validateField('message', formData.message);
    if (!messageValidation.valid) {
      errors.message = messageValidation.error;
      isValid = false;
    }

    setValidationErrors(errors);
    setTouched({ name: true, email: true, subject: true, message: true });
    
    return isValid;
  };

  // Handle form submission
  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);

    if (!validateForm()) {
      setError('Please fix the errors above before submitting');
      return;
    }

    setStatus('submitting');

    try {
      // Prepare payload matching backend SupportFormSubmission model
      const payload = {
        ...formData,
        channel: 'web_form', // Channel metadata
        form_version: FORM_VERSION
      };

      const response = await fetch(apiEndpoint, {
        method: 'POST',
        headers: { 
          'Content-Type': 'application/json',
          'X-Form-Version': FORM_VERSION
        },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Submission failed with status ${response.status}`);
      }

      const data = await response.json();
      setTicketId(data.ticket_id);
      setStatus('success');

      // Callback if provided
      if (onSuccess) onSuccess(data);

    } catch (err) {
      console.error('Form submission error:', err);
      setError(err.message || 'An unexpected error occurred. Please try again.');
      setStatus('error');

      // Callback if provided
      if (onError) onError(err);
    }
  };

  // Handle reset
  const handleReset = () => {
    setStatus('idle');
    setTicketId(null);
    setError(null);
    setFormData({
      name: '',
      email: '',
      subject: '',
      category: 'how-to',
      priority: 'medium',
      message: ''
    });
    setValidationErrors({});
    setTouched({});
  };

  // Render field error
  const renderFieldError = (fieldName) => {
    if (!touched[fieldName] && status !== 'submitting') return null;
    const error = validationErrors[fieldName];
    if (!error) return null;

    return (
      <p className="mt-1 text-sm text-red-600 flex items-center">
        <span className="mr-1">⚠️</span> {error}
      </p>
    );
  };

  // =============================================================================
  // SUCCESS VIEW
  // =============================================================================

  if (status === 'success') {
    return (
      <div className="max-w-2xl mx-auto p-8 bg-white rounded-xl shadow-lg border border-gray-200">
        <div className="text-center">
          {/* Success Icon */}
          <div className="flex justify-center mb-6">
            <CheckCircleIcon />
          </div>

          <h2 className="text-3xl font-bold text-gray-900 mb-3">
            Thank You!
          </h2>
          
          <p className="text-gray-600 mb-6 text-lg">
            Your support request has been submitted successfully.
          </p>

          {/* Ticket ID Card */}
          <div className="bg-gradient-to-r from-blue-50 to-indigo-50 rounded-xl p-6 mb-6 border border-blue-200">
            <p className="text-sm text-gray-600 mb-2 font-medium">Your Ticket ID</p>
            <p className="text-2xl font-mono font-bold text-blue-700 select-all">
              {ticketId}
            </p>
            <p className="text-xs text-gray-500 mt-2">
              📧 Save this for your records
            </p>
          </div>

          {/* Expected Response Time */}
          <div className="bg-gray-50 rounded-lg p-4 mb-6">
            <p className="text-sm text-gray-700">
              <span className="font-semibold">⏱️ Expected Response Time:</span> 
              {' '}Usually within 5 minutes during business hours
            </p>
            <p className="text-xs text-gray-500 mt-2">
              For urgent issues, you'll receive priority handling automatically.
            </p>
          </div>

          {/* Action Buttons */}
          <div className="flex flex-col sm:flex-row gap-3 justify-center">
            <button
              onClick={handleReset}
              className="px-8 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 
                         transition-all duration-200 font-medium shadow-sm hover:shadow-md"
            >
              Submit Another Request
            </button>
            <a
              href="mailto:support@techcorp.com"
              className="px-8 py-3 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200 
                         transition-all duration-200 font-medium text-center"
            >
              Email Support
            </a>
          </div>

          {/* Additional Info */}
          <p className="text-xs text-gray-500 mt-6">
            A confirmation email has been sent to <strong>{formData.email}</strong>
          </p>
        </div>
      </div>
    );
  }

  // =============================================================================
  // ERROR VIEW (After Submission)
  // =============================================================================

  if (status === 'error') {
    return (
      <div className="max-w-2xl mx-auto p-8 bg-white rounded-xl shadow-lg border border-gray-200">
        <div className="text-center">
          {/* Error Icon */}
          <div className="flex justify-center mb-6">
            <ErrorIcon />
          </div>

          <h2 className="text-2xl font-bold text-gray-900 mb-3">
            Submission Failed
          </h2>
          
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
            <p className="text-red-800 text-sm">{error}</p>
          </div>

          {/* Retry Button */}
          <button
            onClick={handleReset}
            className="px-8 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 
                       transition-all duration-200 font-medium shadow-sm"
          >
            Try Again
          </button>

          {/* Alternative Contact */}
          <p className="text-sm text-gray-600 mt-6">
            Having trouble? Email us directly at{' '}
            <a href="mailto:support@techcorp.com" className="text-blue-600 hover:underline">
              support@techcorp.com
            </a>
          </p>
        </div>
      </div>
    );
  }

  // =============================================================================
  // FORM VIEW
  // =============================================================================

  return (
    <div className="max-w-2xl mx-auto p-8 bg-white rounded-xl shadow-lg border border-gray-200">
      {/* Form Header */}
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-gray-900 mb-2">
          Contact Support
        </h2>
        <p className="text-gray-600">
          Fill out the form below and our AI-powered support team will get back to you shortly.
        </p>
      </div>

      {/* Global Error */}
      {error && (
        <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 flex items-start">
          <span className="mr-2 text-lg">❌</span>
          <span>{error}</span>
        </div>
      )}

      {/* Form */}
      <form onSubmit={handleSubmit} className="space-y-6" noValidate>
        
        {/* Name Field */}
        <div>
          <label htmlFor="name" className="block text-sm font-medium text-gray-700 mb-1">
            Your Name <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            id="name"
            name="name"
            value={formData.name}
            onChange={handleChange}
            onBlur={handleBlur}
            required
            disabled={status === 'submitting'}
            className={`w-full px-4 py-2.5 border rounded-lg focus:ring-2 focus:ring-blue-500 
                       focus:border-transparent transition-all duration-200
                       ${validationErrors.name && touched.name 
                         ? 'border-red-300 bg-red-50' 
                         : 'border-gray-300'}`}
            placeholder="John Doe"
            aria-describedby="name-error"
          />
          {renderFieldError('name')}
        </div>

        {/* Email Field */}
        <div>
          <label htmlFor="email" className="block text-sm font-medium text-gray-700 mb-1">
            Email Address <span className="text-red-500">*</span>
          </label>
          <input
            type="email"
            id="email"
            name="email"
            value={formData.email}
            onChange={handleChange}
            onBlur={handleBlur}
            required
            disabled={status === 'submitting'}
            className={`w-full px-4 py-2.5 border rounded-lg focus:ring-2 focus:ring-blue-500 
                       focus:border-transparent transition-all duration-200
                       ${validationErrors.email && touched.email 
                         ? 'border-red-300 bg-red-50' 
                         : 'border-gray-300'}`}
            placeholder="john@example.com"
            aria-describedby="email-error"
          />
          {renderFieldError('email')}
        </div>

        {/* Subject Field */}
        <div>
          <label htmlFor="subject" className="block text-sm font-medium text-gray-700 mb-1">
            Subject <span className="text-red-500">*</span>
          </label>
          <input
            type="text"
            id="subject"
            name="subject"
            value={formData.subject}
            onChange={handleChange}
            onBlur={handleBlur}
            required
            disabled={status === 'submitting'}
            className={`w-full px-4 py-2.5 border rounded-lg focus:ring-2 focus:ring-blue-500 
                       focus:border-transparent transition-all duration-200
                       ${validationErrors.subject && touched.subject 
                         ? 'border-red-300 bg-red-50' 
                         : 'border-gray-300'}`}
            placeholder="Brief description of your issue"
            aria-describedby="subject-error"
          />
          {renderFieldError('subject')}
        </div>

        {/* Category and Priority Row */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          
          {/* Category Field */}
          <div>
            <label htmlFor="category" className="block text-sm font-medium text-gray-700 mb-1">
              Category <span className="text-red-500">*</span>
            </label>
            <select
              id="category"
              name="category"
              value={formData.category}
              onChange={handleChange}
              disabled={status === 'submitting'}
              className="w-full px-4 py-2.5 border border-gray-300 rounded-lg 
                         focus:ring-2 focus:ring-blue-500 focus:border-transparent 
                         transition-all duration-200 bg-white"
            >
              {CATEGORIES.map(cat => (
                <option key={cat.value} value={cat.value}>
                  {cat.icon} {cat.label}
                </option>
              ))}
            </select>
          </div>

          {/* Priority Field */}
          <div>
            <label htmlFor="priority" className="block text-sm font-medium text-gray-700 mb-1">
              Priority
            </label>
            <select
              id="priority"
              name="priority"
              value={formData.priority}
              onChange={handleChange}
              disabled={status === 'submitting'}
              className="w-full px-4 py-2.5 border border-gray-300 rounded-lg 
                         focus:ring-2 focus:ring-blue-500 focus:border-transparent 
                         transition-all duration-200 bg-white"
            >
              {PRIORITIES.map(pri => (
                <option key={pri.value} value={pri.value}>
                  {pri.label}
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Message Field */}
        <div>
          <label htmlFor="message" className="block text-sm font-medium text-gray-700 mb-1">
            How can we help? <span className="text-red-500">*</span>
          </label>
          <textarea
            id="message"
            name="message"
            value={formData.message}
            onChange={handleChange}
            onBlur={handleBlur}
            required
            disabled={status === 'submitting'}
            rows={6}
            maxLength={1000}
            className={`w-full px-4 py-2.5 border rounded-lg focus:ring-2 focus:ring-blue-500 
                       focus:border-transparent transition-all duration-200 resize-none
                       ${validationErrors.message && touched.message 
                         ? 'border-red-300 bg-red-50' 
                         : 'border-gray-300'}`}
            placeholder="Please describe your issue or question in detail. Include any error messages, steps to reproduce, or specific questions you have..."
            aria-describedby="message-error message-counter"
          />
          
          {/* Character Counter */}
          <div className="flex justify-between items-center mt-2">
            {renderFieldError('message')}
            <span 
              id="message-counter"
              className={`text-sm ml-auto ${
                characterCount > 900 ? 'text-red-600' : 'text-gray-500'
              }`}
            >
              {characterCount}/1000 characters
            </span>
          </div>
        </div>

        {/* Info Box */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <p className="text-sm text-blue-800">
            <span className="font-semibold">ℹ️ What happens next?</span>
            <br />
            1. Our AI assistant will analyze your request immediately
            <br />
            2. You'll receive a response via email within 5 minutes
            <br />
            3. Complex issues are automatically escalated to our team
          </p>
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          disabled={!isFormValid || status === 'submitting'}
          className={`w-full py-3.5 px-4 rounded-lg font-medium text-white 
                     transition-all duration-200 shadow-sm
                     ${!isFormValid || status === 'submitting'
                       ? 'bg-gray-400 cursor-not-allowed'
                       : 'bg-blue-600 hover:bg-blue-700 hover:shadow-md'}`}
        >
          {status === 'submitting' ? (
            <span className="flex items-center justify-center">
              <LoadingSpinner />
              Submitting...
            </span>
          ) : (
            'Submit Support Request'
          )}
        </button>

        {/* Privacy Notice */}
        <p className="text-center text-xs text-gray-500">
          By submitting, you agree to our{' '}
          <a href="#" className="text-blue-600 hover:underline">
            Privacy Policy
          </a>{' '}
          and{' '}
          <a href="#" className="text-blue-600 hover:underline">
            Terms of Service
          </a>
        </p>
      </form>
    </div>
  );
}

// =============================================================================
// MOUNT COMPONENT
// =============================================================================

// Mount the React component when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
  const rootElement = document.getElementById('root');
  
  if (rootElement) {
    const root = ReactDOM.createRoot(rootElement);
    root.render(<SupportForm />);
  }
});

// Export for module systems (optional)
if (typeof module !== 'undefined' && module.exports) {
  module.exports = SupportForm;
}
