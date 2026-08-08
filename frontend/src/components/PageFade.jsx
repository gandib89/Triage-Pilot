import { motion, useReducedMotion } from 'framer-motion'

function PageFade({ children }) {
    const reduce = useReducedMotion()

    return (
        <motion.div
            initial={reduce ? false : { opacity: 0, y: 24, filter: 'blur(6px)' }}
            animate={{ opacity: 1, y: 0, filter: 'blur(0px)' }}
            transition={{ duration: 0.7, ease: [0.32, 0.72, 0, 1] }}
        >
            {children}
        </motion.div>
    )
}

export default PageFade
