// core\frontend\js\pages\FullTestExample.tsx
import { BrowserRouter, Route, Routes } from "react-router-dom"
import Layout from "../test-full/layout/Layout"
import AudioTest from "../test-full/pages/AudioTest"
import EntryPoint from "../test-full/pages/EntryPoint"
import LanguagePagePicker from "../test-full/pages/LanguagePagePicker"
import TestFullPagePicker from "../test-full/pages/TestFullPagePicker"

const FullTestExample = () => {
	return (
		<BrowserRouter basename="/full-test-example">
			<Layout>
				<Routes>
					<Route path="/" element={<EntryPoint />} />
					<Route path="/test-full" element={<TestFullPagePicker />} />
					<Route path="/audio-test" element={<AudioTest />} />
					<Route path="/language-test-full" element={<LanguagePagePicker />} />
				</Routes>
			</Layout>
		</BrowserRouter>
	)
}

export default FullTestExample
