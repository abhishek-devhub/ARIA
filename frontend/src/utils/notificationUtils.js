/**
 * Utility for handling browser notifications.
 */

/**
 * Requests permission to show browser notifications.
 * Should be called on user interaction for better support.
 */
export const requestNotificationPermission = async () => {
  if (!('Notification' in window)) {
    console.warn('This browser does not support desktop notification');
    return false;
  }

  if (Notification.permission === 'granted') {
    return true;
  }

  if (Notification.permission !== 'denied') {
    const permission = await Notification.requestPermission();
    return permission === 'granted';
  }

  return false;
};

/**
 * Sends a browser notification.
 * @param {string} title - The notification title.
 * @param {Object} options - Notification options (body, icon, etc.).
 */
export const sendNotification = (title, options = {}) => {
  if (!('Notification' in window) || Notification.permission !== 'granted') {
    return;
  }

  const defaultOptions = {
    icon: '/logo.png', // Fallback if no icon provided
    ...options
  };

  try {
    return new Notification(title, defaultOptions);
  } catch (err) {
    console.error('Failed to send notification:', err);
  }
};
