import type { Preview } from "@storybook/react";
import { AppProviders } from "@/components/providers/app-providers";
import "@/app/globals.css";

const preview: Preview = {
  parameters: {
    controls: {
      matchers: {
        color: /(background|color)$/i,
        date: /Date$/,
      },
    },
    layout: "centered",
  },
  decorators: [
    (Story) => (
      <AppProviders>
        <div className="w-full max-w-md">
          <Story />
        </div>
      </AppProviders>
    ),
  ],
};

export default preview;
