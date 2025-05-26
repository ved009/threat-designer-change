import { useEffect, useState } from "react";
import TopNavigationMFE from "./components/TopNavigationMFE/TopNavigationMFE";
import AppLayoutMFE from "./components/AppLayoutMFE/AppLayoutMFE";
import LoginPageInternal from "./pages/Landingpage/Landingpage";
import { Spinner } from "@cloudscape-design/components";
import { getUser } from "./services/Auth/auth";
import { SpaceBetween } from "@cloudscape-design/components";
import { SplitPanelProvider } from "./SplitPanelContext";
import customTheme from "./customTheme";
import "@cloudscape-design/global-styles/index.css";
import { applyMode, Mode } from "@cloudscape-design/global-styles";
import { applyTheme } from "@cloudscape-design/components/theming";

const App = () => {
  const [loading, setLoading] = useState(true);
  const [authUser, setAuthUser] = useState(null);

  const [colorMode, setColorMode] = useState(() => {
    const savedMode = localStorage.getItem("colorMode");
    return savedMode || "light";
  });

  useEffect(() => {
    checkAuthState();
  }, []);

  useEffect(() => {
    applyMode(colorMode === "light" ? Mode.Light : Mode.Dark);
    localStorage.setItem("colorMode", colorMode);
  }, [colorMode]);

  useEffect(() => {
    applyTheme({ theme: customTheme });
  }, []);

  const toggleColorMode = () => {
    setColorMode((prevMode) => (prevMode === "light" ? "dark" : "light"));
  };

  const checkAuthState = async () => {
    setLoading(true);
    try {
      const user = await getUser();
      setAuthUser(user);
    } catch (error) {
      console.log(error);
      setAuthUser(null);
    } finally {
      setTimeout(() => {
        setLoading(false);
      }, 2000);
    }
  };

  return (
    <div>
      {loading ? (
        <SpaceBetween alignItems="center">
          <div style={{ marginTop: "20px" }}>
            <Spinner size="large" />
          </div>
        </SpaceBetween>
      ) : authUser ? (
        <SplitPanelProvider>
          <TopNavigationMFE
            user={authUser}
            setAuthUser={checkAuthState}
            colorMode={colorMode}
            toggleColorMode={toggleColorMode}
          />
          <AppLayoutMFE user={authUser} colorMode={colorMode} toggleColorMode={toggleColorMode} />
        </SplitPanelProvider>
      ) : (
        <LoginPageInternal setAuthUser={checkAuthState} />
      )}
    </div>
  );
};

export default App;
