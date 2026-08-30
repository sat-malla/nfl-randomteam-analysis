import { GluestackUIProvider } from "@/components/ui/gluestack-ui-provider";
import { Slot } from "expo-router";
import { getAnalytics, logScreenView } from "@react-native-firebase/analytics";
import { usePathname } from "expo-router";
import { useEffect } from "react";

import "@/global.css";

// function useScreenTracking() {
//   const pathname = usePathname();
//   const analyticsInstance = getAnalytics();

//   useEffect(() => {
//     logScreenView(analyticsInstance, {
//       screen_name: pathname,
//       screen_class: pathname,
//     });
//   }, [pathname]);
// }

export default function RootLayout() {
 // useScreenTracking();

  return (
    <GluestackUIProvider>
      <Slot />
    </GluestackUIProvider>
  );
}
