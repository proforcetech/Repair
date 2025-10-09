import { useCallback, useEffect, useRef, useState } from "react";

import type { Appointment } from "@/services/appointments";

export type AppointmentSocketEvent =
  | { type: "created"; appointment: Appointment }
  | { type: "updated"; appointment: Appointment }
  | { type: "deleted"; appointmentId: string };

type Subscriber = (event: AppointmentSocketEvent) => void;

/**
 * useAppointmentsSocket is a lightweight mock of the realtime channel that the
 * schedule workspace will eventually consume.  It keeps a registry of
 * subscribers and exposes a trigger helper so tests can simulate inbound
 * events without an actual WebSocket connection.
 */
export function useAppointmentsSocket(onMessage?: Subscriber) {
  const subscribers = useRef(new Set<Subscriber>());
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    if (onMessage) {
      subscribers.current.add(onMessage);
      return () => {
        subscribers.current.delete(onMessage);
      };
    }

    return undefined;
  }, [onMessage]);

  useEffect(() => {
    setConnected(true);
    return () => {
      setConnected(false);
      subscribers.current.clear();
    };
  }, []);

  const triggerMockEvent = useCallback((event: AppointmentSocketEvent) => {
    subscribers.current.forEach((subscriber) => {
      try {
        subscriber(event);
      } catch (error) {
        console.error("Mock socket subscriber failed", error);
      }
    });
  }, []);

  const subscribe = useCallback((listener: Subscriber) => {
    subscribers.current.add(listener);
    return () => subscribers.current.delete(listener);
  }, []);

  return { connected, triggerMockEvent, subscribe };
}
