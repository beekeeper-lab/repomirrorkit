import { createMachine } from "xstate";

export const orderMachine = createMachine({
  id: "order",
  initial: "draft",
  states: {
    draft: { on: { SUBMIT: "submitted", CANCEL: "cancelled" } },
    submitted: {
      on: {
        PAY: { target: "paid", guard: "hasPaymentMethod" },
        CANCEL: "cancelled",
      },
    },
    paid: { on: { SHIP: "shipped" } },
    shipped: { type: "final" },
    cancelled: { type: "final" },
  },
});
