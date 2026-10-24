import { useEffect, useRef } from 'react';

/**
 * Custom hook that invokes callback whenever the document visibility changes back to visible
 * @param {Function} onVisible - Callback function to execute when tab becomes active
 */
export const useVisibilityChange = (onVisible) => {
  const savedCallback = useRef(onVisible);

  useEffect(() => {
    savedCallback.current = onVisible;
  }, [onVisible]);

  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible' && savedCallback.current) {
        savedCallback.current();
      }
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, []);
};

export default useVisibilityChange;
